"""Server management (owner of a Discord server and the members they choose): access rules, settings, journal.

The bot keeps a copy of each server in guild_meta / guild_channels / guild_roles / guild_members (owner, its own
permissions, text channels, roles, current members). The website reads it to decide who manages a server and to
show the channels and roles, so it never needs the bot token. Settings are written here and applied by the bot.

Who manages a server, checked again at every request (never trusted from the login session):
  - its owner: guild_meta.owner_id, as Discord reports it to the bot right now;
  - the managers the owner chose (server_managers) while they are still members of the server (guild_members).
The list of managers and the private mode are the owner's only.
"""

import logging
from datetime import datetime, timedelta, timezone
from zoneinfo import available_timezones

from app.cache import cache
from app.database import create_tables, db

log = logging.getLogger(__name__)

DEFAULT_TIMEZONE = "Europe/Paris"
MAX_MANAGERS = 10
ACCESS_CACHE_SECONDS = 15  # owner and member checks: short, a change on Discord shows up quickly

TABLES = [
    # Automatic roles (also created by the bot, same definitions)
    """CREATE TABLE IF NOT EXISTS server_roles (
        server_id BIGINT PRIMARY KEY,
        enabled BOOLEAN NOT NULL DEFAULT FALSE,
        keep_highest BOOLEAN NOT NULL DEFAULT FALSE,
        remove_unmet BOOLEAN NOT NULL DEFAULT TRUE,
        updated_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT NOW(),
        updated_by BIGINT
    )""",
    """CREATE TABLE IF NOT EXISTS server_role_rules (
        id BIGSERIAL PRIMARY KEY,
        server_id BIGINT NOT NULL,
        position INTEGER NOT NULL DEFAULT 0,
        role_id BIGINT NOT NULL,
        match VARCHAR(3) NOT NULL DEFAULT 'all',
        conditions TEXT NOT NULL
    )""",
    "CREATE INDEX IF NOT EXISTS server_role_rules_server ON server_role_rules (server_id, position)",
    """CREATE TABLE IF NOT EXISTS server_role_ladders (
        id BIGSERIAL PRIMARY KEY,
        server_id BIGINT NOT NULL,
        position INTEGER NOT NULL DEFAULT 0,
        keep_highest BOOLEAN NOT NULL DEFAULT TRUE
    )""",
    "CREATE INDEX IF NOT EXISTS server_role_ladders_server ON server_role_ladders (server_id, position)",
    """CREATE TABLE IF NOT EXISTS server_role_tiers (
        id BIGSERIAL PRIMARY KEY,
        ladder_id BIGINT NOT NULL,
        server_id BIGINT NOT NULL,
        position INTEGER NOT NULL DEFAULT 0,
        role_id BIGINT NOT NULL,
        match VARCHAR(3) NOT NULL DEFAULT 'all',
        conditions TEXT NOT NULL
    )""",
    "CREATE INDEX IF NOT EXISTS server_role_tiers_server ON server_role_tiers (server_id, ladder_id, position)",
    """CREATE TABLE IF NOT EXISTS role_grants (
        server_id BIGINT NOT NULL,
        user_id BIGINT NOT NULL,
        role_id BIGINT NOT NULL,
        granted_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT NOW(),
        PRIMARY KEY (server_id, user_id, role_id)
    )""",
    # Automatic reports (also created by the bot, same definitions)
    """CREATE TABLE IF NOT EXISTS server_reports (
        server_id BIGINT NOT NULL,
        kind VARCHAR(8) NOT NULL,
        enabled BOOLEAN NOT NULL DEFAULT FALSE,
        channel_id BIGINT,
        hour SMALLINT NOT NULL DEFAULT 20,
        weekday SMALLINT NOT NULL DEFAULT 6,
        mention_role_id BIGINT,
        updated_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT NOW(),
        updated_by BIGINT,
        PRIMARY KEY (server_id, kind)
    )""",
    """CREATE TABLE IF NOT EXISTS report_runs (
        server_id BIGINT NOT NULL,
        kind VARCHAR(8) NOT NULL,
        period_start DATE NOT NULL,
        sent_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT NOW(),
        ok BOOLEAN,
        detail TEXT,
        PRIMARY KEY (server_id, kind, period_start)
    )""",
    """CREATE TABLE IF NOT EXISTS report_requests (
        id BIGSERIAL PRIMARY KEY,
        server_id BIGINT NOT NULL,
        kind VARCHAR(8) NOT NULL,
        requested_by BIGINT,
        created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT NOW(),
        done_at TIMESTAMP WITHOUT TIME ZONE,
        ok BOOLEAN,
        detail TEXT
    )""",
    "CREATE INDEX IF NOT EXISTS report_requests_pending ON report_requests (created_at) WHERE done_at IS NULL",
    # Level-up announcements (also created by the bot, same definition)
    """CREATE TABLE IF NOT EXISTS server_levelup (
        server_id BIGINT PRIMARY KEY,
        enabled BOOLEAN NOT NULL DEFAULT FALSE,
        channel_id BIGINT,
        same_channel BOOLEAN NOT NULL DEFAULT FALSE,
        message TEXT,
        mention BOOLEAN NOT NULL DEFAULT TRUE,
        min_level INTEGER NOT NULL DEFAULT 2,
        every INTEGER NOT NULL DEFAULT 1,
        with_card BOOLEAN NOT NULL DEFAULT TRUE,
        updated_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT NOW(),
        updated_by BIGINT
    )""",
    """CREATE TABLE IF NOT EXISTS server_settings (
        server_id BIGINT PRIMARY KEY,
        timezone VARCHAR(64) NOT NULL DEFAULT 'Europe/Paris',
        private BOOLEAN NOT NULL DEFAULT FALSE,
        updated_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT NOW(),
        updated_by BIGINT
    )""",
    """CREATE TABLE IF NOT EXISTS server_managers (
        server_id BIGINT NOT NULL,
        user_id BIGINT NOT NULL,
        added_by BIGINT,
        added_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT NOW(),
        PRIMARY KEY (server_id, user_id)
    )""",
    "CREATE INDEX IF NOT EXISTS server_managers_user ON server_managers (user_id)",
    # Also created by the bot (same definition): whichever starts first
    """CREATE TABLE IF NOT EXISTS server_feature_log (
        id BIGSERIAL PRIMARY KEY,
        server_id BIGINT NOT NULL,
        created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT NOW(),
        feature VARCHAR(16) NOT NULL,
        action VARCHAR(32) NOT NULL,
        actor_id BIGINT,
        target_id BIGINT,
        ok BOOLEAN NOT NULL DEFAULT TRUE,
        detail TEXT
    )""",
    "CREATE INDEX IF NOT EXISTS server_feature_log_server ON server_feature_log (server_id, created_at DESC)",
    "CREATE INDEX IF NOT EXISTS server_feature_log_created ON server_feature_log (created_at)",
]

# Discord permission bits the bot needs (key, bit); their names and uses are in permission_texts()
PERMISSIONS = [
    ("view", 1 << 10), ("send", 1 << 11), ("embed", 1 << 14), ("history", 1 << 16), ("roles", 1 << 28),
]


def permission_texts(lang: str) -> dict[str, tuple[str, str]]:
    """{key: (name, what it is for)} of each permission the bot needs."""
    from app.i18n import tr
    return {
        "view": (tr("Voir les salons", "View channels", lang), tr("Pour lire les salons où il doit écrire.", "To see the channels it must write in.", lang)),
        "send": (tr("Envoyer des messages", "Send messages", lang), tr("Annonces de niveau et rapports.", "Level-up announcements and reports.", lang)),
        "embed": (tr("Intégrer des liens", "Embed links", lang), tr("Cartes images des annonces et des rapports.", "Image cards of announcements and reports.", lang)),
        "history": (tr("Voir l’historique", "Read message history", lang), tr("Répondre dans le bon salon.", "Reply in the right channel.", lang)),
        "roles": (tr("Gérer les rôles", "Manage roles", lang), tr("Rôles automatiques.", "Automatic roles.", lang)),
    }


ADMINISTRATOR = 1 << 3
BOT_CLIENT_ID = "1210665993328926750"
INVITE_PERMISSIONS = sum(bit for _, bit in PERMISSIONS)
_enabled = True


def ensure_tables() -> None:
    global _enabled
    error = create_tables(TABLES)
    if error is not None:
        _enabled = False
        log.warning("Server management disabled (tables unavailable, run the web migrations): %s", error)


def invite_url(server_id: int | str | None = None) -> str:
    """Bot invitation with the permissions the features need; on a server's page, that server is preselected."""
    url = (f"https://discord.com/oauth2/authorize?client_id={BOT_CLIENT_ID}"
           f"&permissions={INVITE_PERMISSIONS}&scope=bot%20applications.commands")
    if server_id:
        url += f"&guild_id={int(server_id)}&disable_guild_select=true"
    return url


def _rows(sql: str, params=()) -> list[tuple]:
    try:
        return db.execute_sql(sql, params).fetchall()
    except Exception:
        db.rollback()  # guild_* missing: the bot has not been updated yet
        return []


def _now() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


# ------------------------------------------------------------------------------------------------ the bot's copy
def guild_meta(server_id: int) -> dict | None:
    """What the bot knows of the server right now, or None when it never copied it (old bot, or never there)."""
    def load():
        rows = _rows("SELECT owner_id, locale, bot_permissions, bot_top_role_position, member_count, bot_present, synced_at, "
                     "members_synced_at FROM guild_meta WHERE server_id = %s", (int(server_id),))
        if not rows:
            return None
        owner, locale, perms, top, count, present, synced, members_synced = rows[0]
        return {"owner_id": int(owner or 0), "locale": locale or "", "bot_permissions": int(perms or 0),
                "bot_top_role_position": int(top or 0), "member_count": int(count or 0), "bot_present": bool(present),
                "synced_at": synced, "members_synced_at": members_synced}
    return cache.get_or_set(("guild_meta", int(server_id)), ACCESS_CACHE_SECONDS, load)


def is_member(user_id: int, server_id: int) -> bool:
    """Member of the server right now (the bot's live list, not "has stats there": someone who left is not)."""
    def load():
        return bool(_rows("SELECT 1 FROM guild_members WHERE server_id = %s AND user_id = %s", (int(server_id), int(user_id))))
    return cache.get_or_set(("guild_member", int(server_id), int(user_id)), ACCESS_CACHE_SECONDS, load)


# Preview period: server management is open to the site admins only (ADMIN_USER_IDS) until it is ready for every
# owner. Set to True to open it to all owners and their managers.
OPEN_TO_ALL = False


def preview_allowed(user_id: int | str | None) -> bool:
    """Server management is visible to this member (everyone once OPEN_TO_ALL, the site admins until then)."""
    from app.config import Config
    return bool(user_id) and (OPEN_TO_ALL or str(user_id) in Config.ADMIN_USER_IDS)


def server_role(user_id: int | str | None, server_id: int) -> str | None:
    """"owner", "manager" or None for this visitor on this server."""
    if not user_id or not _enabled or not preview_allowed(user_id):
        return None
    uid = int(user_id)
    meta = guild_meta(server_id)
    if not meta:
        return None
    if meta["owner_id"] == uid:
        return "owner"
    if _rows("SELECT 1 FROM server_managers WHERE server_id = %s AND user_id = %s", (int(server_id), uid)) and is_member(uid, server_id):
        return "manager"
    return None


def managed_servers(user_id: int | str | None) -> list[dict]:
    """Servers this member owns or manages (account menu, "My servers"), the bot present first."""
    if not user_id or not _enabled or not preview_allowed(user_id):
        return []
    uid = int(user_id)

    def load():
        rows = _rows(
            "SELECT m.server_id, s.servername, s.avatar, m.bot_present, "
            "CASE WHEN m.owner_id = %s THEN 'owner' ELSE 'manager' END "
            "FROM guild_meta m LEFT JOIN servers s ON s.server_id = m.server_id "
            "WHERE m.owner_id = %s OR (EXISTS (SELECT 1 FROM server_managers sm WHERE sm.server_id = m.server_id AND sm.user_id = %s) "
            "AND EXISTS (SELECT 1 FROM guild_members gm WHERE gm.server_id = m.server_id AND gm.user_id = %s)) "
            "ORDER BY m.bot_present DESC, s.servername", (uid, uid, uid, uid))
        return [{"server_id": str(sid), "name": name or f"#{sid}", "avatar": avatar, "bot_present": bool(present), "role": role}
                for sid, name, avatar, present, role in rows]
    return cache.get_or_set(("managed_servers", uid), ACCESS_CACHE_SECONDS, load)


def channels(server_id: int) -> list[dict]:
    rows = _rows("SELECT channel_id, name, kind, category, can_view, can_send, can_embed, can_attach FROM guild_channels "
                 "WHERE server_id = %s ORDER BY position, name", (int(server_id),))
    return [{"id": str(cid), "name": name, "kind": kind, "category": cat or "", "can_view": v, "can_send": s,
             "can_embed": e, "can_attach": a} for cid, name, kind, cat, v, s, e, a in rows]


def roles(server_id: int) -> list[dict]:
    rows = _rows("SELECT role_id, name, color, position, managed, assignable, dangerous FROM guild_roles "
                 "WHERE server_id = %s ORDER BY position DESC", (int(server_id),))
    return [{"id": str(rid), "name": name, "color": f"#{int(color or 0):06x}" if color else None, "position": pos,
             "managed": managed, "assignable": assignable, "dangerous": dangerous}
            for rid, name, color, pos, managed, assignable, dangerous in rows]


def diagnostics(server_id: int, lang: str) -> dict:
    """What the bot may do on the server: each needed permission, and the channels it cannot write in."""
    meta = guild_meta(server_id) or {}
    perms = meta.get("bot_permissions", 0)
    admin = bool(perms & ADMINISTRATOR)
    texts = permission_texts(lang)
    checks = [{"key": key, "ok": admin or bool(perms & bit), "label": texts[key][0], "why": texts[key][1]}
              for key, bit in PERMISSIONS]
    chans = channels(server_id)
    return {
        "synced": bool(meta),
        "bot_present": meta.get("bot_present", False),
        "synced_at": meta.get("synced_at"),
        "admin": admin,
        "checks": checks,
        "missing": [c for c in checks if not c["ok"]],
        "channels_total": len(chans),
        "channels_blocked": [c for c in chans if not c["can_send"]],
    }


# ------------------------------------------------------------------------------------------------ settings
def get_settings(server_id: int) -> dict:
    rows = _rows("SELECT timezone, private, updated_at, updated_by FROM server_settings WHERE server_id = %s", (int(server_id),))
    if not rows:
        return {"timezone": DEFAULT_TIMEZONE, "private": False, "updated_at": None, "updated_by": None}
    tz, private, at, by = rows[0]
    return {"timezone": tz or DEFAULT_TIMEZONE, "private": bool(private), "updated_at": at, "updated_by": by}


def timezone_choices() -> list[str]:
    """IANA zones of the form Region/City (no aliases such as "UTC" or "Etc/GMT+3"), sorted."""
    def load():
        keep = ("Africa/", "America/", "Asia/", "Atlantic/", "Australia/", "Europe/", "Indian/", "Pacific/")
        return sorted(z for z in available_timezones() if z.startswith(keep))
    return cache.get_or_set(("timezone_choices",), 86400, load)


def save_timezone(server_id: int, tz: str, by: int) -> bool:
    if tz not in timezone_choices():
        return False
    before = get_settings(server_id)["timezone"]
    try:
        db.execute_sql(
            "INSERT INTO server_settings (server_id, timezone, updated_at, updated_by) VALUES (%s, %s, %s, %s) "
            "ON CONFLICT (server_id) DO UPDATE SET timezone = EXCLUDED.timezone, updated_at = EXCLUDED.updated_at, "
            "updated_by = EXCLUDED.updated_by", (int(server_id), tz, _now(), int(by)))
    except Exception:
        db.rollback()
        return False
    if before != tz:
        log_action(server_id, "general", "timezone", actor=by, detail=f"{before} → {tz}")
    return True


# ------------------------------------------------------------------------------------------------ level-ups
LEVELUP_EVERY = (1, 2, 5, 10)
# Text posted when the server leaves the message empty, in its language (same as the bot, handlers/i18n.go)
LEVELUP_DEFAULT_MESSAGES = {
    "en": "🎉 {membre} reached **level {niveau}**!",
    "fr": "🎉 {membre} passe au **niveau {niveau}** !",
    "es": "🎉 ¡{membre} sube al **nivel {niveau}**!",
    "pt": "🎉 {membre} chegou ao **nível {niveau}**!",
    "it": "🎉 {membre} sale al **livello {niveau}**!",
    "de": "🎉 {membre} erreicht **Level {niveau}**!",
    "pl": "🎉 {membre} awansuje na **poziom {niveau}**!",
    "tr": "🎉 {membre} **{niveau}. seviyeye** ulaştı!",
    "ru": "🎉 {membre} достигает **уровня {niveau}**!",
    "hi": "🎉 {membre} **लेवल {niveau}** पर पहुँचे!",
    "ja": "🎉 {membre} が**レベル {niveau}** になりました！",
    "ko": "🎉 {membre} 님이 **레벨 {niveau}**에 도달했어요!",
}


def levelup_default_message(locale: str | None) -> str:
    code = (locale or "").split("-")[0].lower()
    return LEVELUP_DEFAULT_MESSAGES.get(code, LEVELUP_DEFAULT_MESSAGES["en"])


LEVELUP_MAX_MESSAGE = 300
LEVELUP_DEFAULTS = {"enabled": False, "channel_id": None, "same_channel": False, "message": "", "mention": True,
                    "min_level": 2, "every": 1, "with_card": True, "updated_at": None}


def get_levelup(server_id: int) -> dict:
    rows = _rows("SELECT enabled, channel_id, same_channel, message, mention, min_level, every, with_card, updated_at "
                 "FROM server_levelup WHERE server_id = %s", (int(server_id),))
    if not rows:
        return dict(LEVELUP_DEFAULTS)
    enabled, channel, same, message, mention, min_level, every, card, at = rows[0]
    return {"enabled": bool(enabled), "channel_id": str(channel) if channel else None, "same_channel": bool(same),
            "message": message or "", "mention": bool(mention), "min_level": int(min_level), "every": int(every),
            "with_card": bool(card), "updated_at": at}


def save_levelup(server_id: int, form: dict, by: int) -> str | None:
    """Validated save of the announcement settings. None when saved, else the reason: "channel", "error"."""
    known = {c["id"]: c for c in channels(server_id)}
    enabled = form.get("enabled") == "1"
    channel = form.get("channel_id") or ""
    if channel and channel not in known:
        return "channel"
    if enabled and not channel:
        return "channel"
    try:
        min_level = max(1, min(500, int(form.get("min_level") or 2)))
    except ValueError:
        min_level = 2
    try:
        every = int(form.get("every") or 1)
    except ValueError:
        every = 1
    if every not in LEVELUP_EVERY:
        every = 1
    message = (form.get("message") or "").replace("\r", "").strip()[:LEVELUP_MAX_MESSAGE]
    values = {"enabled": enabled, "channel_id": int(channel) if channel else None, "same_channel": form.get("same_channel") == "1",
              "message": message or None, "mention": form.get("mention") == "1", "min_level": min_level, "every": every,
              "with_card": form.get("with_card") == "1"}
    before = get_levelup(server_id)
    try:
        db.execute_sql(
            "INSERT INTO server_levelup (server_id, enabled, channel_id, same_channel, message, mention, min_level, every, with_card, "
            "updated_at, updated_by) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s) "
            "ON CONFLICT (server_id) DO UPDATE SET enabled = EXCLUDED.enabled, channel_id = EXCLUDED.channel_id, "
            "same_channel = EXCLUDED.same_channel, message = EXCLUDED.message, mention = EXCLUDED.mention, "
            "min_level = EXCLUDED.min_level, every = EXCLUDED.every, with_card = EXCLUDED.with_card, "
            "updated_at = EXCLUDED.updated_at, updated_by = EXCLUDED.updated_by",
            (int(server_id), values["enabled"], values["channel_id"], values["same_channel"], values["message"], values["mention"],
             values["min_level"], values["every"], values["with_card"], _now(), int(by)))
    except Exception:
        db.rollback()
        return "error"
    # Journal: turned on / off, or settings changed
    if before["enabled"] != enabled:
        action = "levels_on" if enabled else "levels_off"
    else:
        action = "levels_settings"
    channel_name = known[channel]["name"] if channel else ""
    log_action(server_id, "levels", action, actor=by, detail=f"#{channel_name}" if channel_name else None)
    return None


# ------------------------------------------------------------------------------------------------ reports
REPORT_KINDS = ("daily", "weekly", "monthly")
REPORT_DEFAULTS = {
    "daily": {"hour": 21, "weekday": 6},
    "weekly": {"hour": 20, "weekday": 6},    # Sunday evening
    "monthly": {"hour": 10, "weekday": 6},   # the 1st in the morning
}
REPORT_TEST_COOLDOWN = 120  # seconds between two tests of a server (the bot handles them within a minute)


def get_reports(server_id: int) -> dict:
    out = {kind: {"enabled": False, "channel_id": None, "hour": REPORT_DEFAULTS[kind]["hour"], "weekday": REPORT_DEFAULTS[kind]["weekday"],
                  "mention_role_id": None, "updated_at": None} for kind in REPORT_KINDS}
    for kind, enabled, channel, hour, weekday, role, at in _rows(
            "SELECT kind, enabled, channel_id, hour, weekday, mention_role_id, updated_at FROM server_reports WHERE server_id = %s",
            (int(server_id),)):
        if kind in out:
            out[kind] = {"enabled": bool(enabled), "channel_id": str(channel) if channel else None, "hour": int(hour),
                         "weekday": int(weekday), "mention_role_id": str(role) if role else None, "updated_at": at}
    return out


def save_reports(server_id: int, form: dict, by: int) -> str | None:
    """Validated save of the three reports. None when saved, else "channel:<kind>" or "error"."""
    known_channels = {c["id"]: c for c in channels(server_id)}
    known_roles = {r["id"] for r in roles(server_id) if not r["managed"]}
    before = get_reports(server_id)
    values = {}
    for kind in REPORT_KINDS:
        enabled = form.get(f"{kind}_enabled") == "1"
        channel = form.get(f"{kind}_channel") or ""
        if channel and channel not in known_channels:
            channel = ""
        if enabled and not channel:
            return f"channel:{kind}"
        try:
            hour = min(23, max(0, int(form.get(f"{kind}_hour", REPORT_DEFAULTS[kind]["hour"]))))
        except ValueError:
            hour = REPORT_DEFAULTS[kind]["hour"]
        try:
            weekday = min(6, max(0, int(form.get(f"{kind}_weekday", REPORT_DEFAULTS[kind]["weekday"]))))
        except ValueError:
            weekday = REPORT_DEFAULTS[kind]["weekday"]
        role = form.get(f"{kind}_role") or ""
        values[kind] = (enabled, int(channel) if channel else None, hour, weekday, int(role) if role in known_roles else None)
    try:
        for kind, (enabled, channel, hour, weekday, role) in values.items():
            db.execute_sql(
                "INSERT INTO server_reports (server_id, kind, enabled, channel_id, hour, weekday, mention_role_id, updated_at, updated_by) "
                "VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s) ON CONFLICT (server_id, kind) DO UPDATE SET enabled = EXCLUDED.enabled, "
                "channel_id = EXCLUDED.channel_id, hour = EXCLUDED.hour, weekday = EXCLUDED.weekday, mention_role_id = EXCLUDED.mention_role_id, "
                "updated_at = EXCLUDED.updated_at, updated_by = EXCLUDED.updated_by",
                (int(server_id), kind, enabled, channel, hour, weekday, role, _now(), int(by)))
    except Exception:
        db.rollback()
        return "error"
    for kind, (enabled, channel, hour, weekday, role) in values.items():
        old = before[kind]
        changed = (old["enabled"], old["channel_id"], old["hour"], old["weekday"], old["mention_role_id"]) !=             (enabled, str(channel) if channel else None, hour, weekday, str(role) if role else None)
        if not changed:
            continue
        action = ("reports_on" if enabled else "reports_off") if old["enabled"] != enabled else "reports_settings"
        name = known_channels.get(str(channel), {}).get("name") if channel else None
        log_action(server_id, "reports", action, actor=by, detail=kind + (f" · #{name}" if name else ""))
    return None


def request_report_test(server_id: int, kind: str, by: int) -> str | None:
    """Ask the bot for a test report (the last finished period). None when asked, else "channel", "wait" or "error"."""
    if kind not in REPORT_KINDS:
        return "error"
    if not get_reports(server_id)[kind]["channel_id"]:
        return "channel"
    recent = _rows("SELECT 1 FROM report_requests WHERE server_id = %s AND created_at > %s",
                   (int(server_id), _now() - timedelta(seconds=REPORT_TEST_COOLDOWN)))
    if recent:
        return "wait"
    try:
        db.execute_sql("INSERT INTO report_requests (server_id, kind, requested_by, created_at) VALUES (%s, %s, %s, %s)",
                       (int(server_id), kind, int(by), _now()))
    except Exception:
        db.rollback()
        return "error"
    return None


def report_history(server_id: int, limit: int = 12) -> list[dict]:
    """Last reports sent and tests asked, newest first (for the Reports tab)."""
    rows = _rows(
        "SELECT * FROM (SELECT sent_at AS at, kind, period_start::text AS period, ok, detail, FALSE AS test, FALSE AS pending "
        "FROM report_runs WHERE server_id = %s "
        "UNION ALL SELECT created_at, kind, NULL, ok, detail, TRUE, done_at IS NULL AND created_at > %s FROM report_requests WHERE server_id = %s) x "
        "ORDER BY at DESC LIMIT %s",
        (int(server_id), _now() - timedelta(hours=1), int(server_id), limit))
    return [{"at": at, "kind": kind, "period": period, "ok": ok, "detail": detail, "test": test, "pending": pending}
            for at, kind, period, ok, detail, test, pending in rows]


# ------------------------------------------------------------------------------------------------ automatic roles
# A rule is a progression of tiers (10 h -> Regular, 50 h -> Veteran, 100 h -> Legend): each tier gives one role
# when its conditions are met; the rule stacks the roles of every tier met, or keeps the highest one only.
MAX_ROLE_RULES = 10
MAX_ROLE_TIERS = 10        # per rule
MAX_ROLE_TIERS_TOTAL = 30  # per server
MAX_ROLE_CONDITIONS = 3    # per tier
ROLE_METRICS = ("voice", "messages", "level")
ROLE_SCOPES = ("total", "30d")
ROLE_LIMITS = {"voice": 100000, "messages": 10000000, "level": 500}  # highest threshold accepted per metric


def _tier(role, match, conditions) -> dict | None:
    import json

    try:
        conds = json.loads(conditions)
    except ValueError:
        return None
    return {"role_id": str(role), "match": match if match in ("all", "any") else "all", "conditions": conds}


def get_roles_settings(server_id: int) -> dict:
    """The automatic roles of a server: switches and rules (each with its tiers), in the order of the page."""
    sid = int(server_id)
    out = {"enabled": False, "remove_unmet": True, "updated_at": None, "rules": []}
    rows = _rows("SELECT enabled, keep_highest, remove_unmet, updated_at FROM server_roles WHERE server_id = %s", (sid,))
    old_keep = False
    if rows:
        enabled, old_keep, remove, at = rows[0]
        out.update(enabled=bool(enabled), remove_unmet=bool(remove), updated_at=at)
    ladders = {}
    for ladder_id, keep, role, match, conditions in _rows(
            "SELECT l.id, l.keep_highest, t.role_id, t.match, t.conditions FROM server_role_ladders l "
            "JOIN server_role_tiers t ON t.ladder_id = l.id WHERE l.server_id = %s ORDER BY l.position, l.id, t.position, t.id", (sid,)):
        if ladder_id not in ladders:
            ladders[ladder_id] = {"keep_highest": bool(keep), "tiers": []}
            out["rules"].append(ladders[ladder_id])
        tier = _tier(role, match, conditions)
        if tier:
            ladders[ladder_id]["tiers"].append(tier)
    if not out["rules"]:
        # Rules of web 3.46.0 not yet turned into tiers by the bot: shown as one rule, as they worked
        old = [t for t in (_tier(r, m, c) for r, m, c in _rows(
            "SELECT role_id, match, conditions FROM server_role_rules WHERE server_id = %s ORDER BY position, id", (sid,))) if t]
        if old:
            out["rules"].append({"keep_highest": bool(old_keep), "tiers": old})
    return out


def _parse_tier(item, known_roles: dict) -> tuple[dict | None, str | None]:
    if not isinstance(item, dict):
        return None, "invalid"
    role = str(item.get("role_id") or "")
    if role not in known_roles:
        return None, "role"
    if known_roles[role]["dangerous"] or known_roles[role]["managed"]:
        return None, "dangerous"
    match = item.get("match") if item.get("match") in ("all", "any") else "all"
    conds = item.get("conditions")
    if not isinstance(conds, list) or not 1 <= len(conds) <= MAX_ROLE_CONDITIONS:
        return None, "invalid"
    clean = []
    for c in conds:
        if not isinstance(c, dict) or c.get("metric") not in ROLE_METRICS:
            return None, "invalid"
        metric = c["metric"]
        scope = "total" if metric == "level" else (c.get("scope") if c.get("scope") in ROLE_SCOPES else "total")
        try:
            value = int(float(c.get("min")))
        except (TypeError, ValueError, OverflowError):
            return None, "invalid"
        if not 1 <= value <= ROLE_LIMITS[metric]:
            return None, "invalid"
        clean.append({"metric": metric, "scope": scope, "min": value})
    return {"role_id": role, "match": match, "conditions": clean}, None


def parse_role_rules(raw: str, known_roles: dict) -> tuple[list[dict] | None, str | None]:
    """Rules sent by the page (JSON: [{keep_highest, tiers: [{role_id, match, conditions}]}]), checked one by one:
    (rules, None) or (None, reason). Reasons: "invalid" (malformed), "role" (unknown role), "dangerous" (moderation
    rights or managed role), "full" (too many rules or tiers)."""
    import json

    try:
        data = json.loads(raw or "[]")
    except ValueError:
        return None, "invalid"
    if not isinstance(data, list):
        return None, "invalid"
    if len(data) > MAX_ROLE_RULES:
        return None, "full"
    rules, total = [], 0
    for item in data:
        if not isinstance(item, dict) or not isinstance(item.get("tiers"), list) or not item["tiers"]:
            return None, "invalid"
        if len(item["tiers"]) > MAX_ROLE_TIERS:
            return None, "full"
        total += len(item["tiers"])
        if total > MAX_ROLE_TIERS_TOTAL:
            return None, "full"
        tiers = []
        for t in item["tiers"]:
            tier, error = _parse_tier(t, known_roles)
            if error:
                return None, error
            tiers.append(tier)
        rules.append({"keep_highest": item.get("keep_highest") is True, "tiers": tiers})
    return rules, None


def save_roles(server_id: int, form: dict, by: int) -> str | None:
    """Validated save of the automatic roles. None when saved, else the reason: "invalid", "role", "dangerous",
    "full", "empty" (turned on without a rule) or "error"."""
    import json

    sid = int(server_id)
    known = {r["id"]: r for r in roles(sid)}
    rules, error = parse_role_rules(form.get("rules_json", ""), known)
    if error:
        return error
    enabled = form.get("enabled") == "1"
    if enabled and not rules:
        return "empty"
    remove = form.get("remove_unmet") == "1"
    before = get_roles_settings(sid)
    try:
        with db.atomic():
            db.execute_sql(
                "INSERT INTO server_roles (server_id, enabled, remove_unmet, updated_at, updated_by) VALUES (%s, %s, %s, %s, %s) "
                "ON CONFLICT (server_id) DO UPDATE SET enabled = EXCLUDED.enabled, remove_unmet = EXCLUDED.remove_unmet, "
                "updated_at = EXCLUDED.updated_at, updated_by = EXCLUDED.updated_by",
                (sid, enabled, remove, _now(), int(by)))
            db.execute_sql("DELETE FROM server_role_tiers WHERE server_id = %s", (sid,))
            db.execute_sql("DELETE FROM server_role_ladders WHERE server_id = %s", (sid,))
            db.execute_sql("DELETE FROM server_role_rules WHERE server_id = %s", (sid,))  # web 3.46.0 rows, replaced
            for position, rule in enumerate(rules):
                ladder_id = db.execute_sql(
                    "INSERT INTO server_role_ladders (server_id, position, keep_highest) VALUES (%s, %s, %s) RETURNING id",
                    (sid, position, rule["keep_highest"])).fetchone()[0]
                for tier_position, tier in enumerate(rule["tiers"]):
                    db.execute_sql(
                        "INSERT INTO server_role_tiers (ladder_id, server_id, position, role_id, match, conditions) VALUES (%s, %s, %s, %s, %s, %s)",
                        (ladder_id, sid, tier_position, int(tier["role_id"]), tier["match"], json.dumps(tier["conditions"])))
    except Exception:
        db.rollback()
        return "error"
    changed = (before["enabled"], before["remove_unmet"], before["rules"]) != (enabled, remove, rules)
    if changed:
        action = ("roles_on" if enabled else "roles_off") if before["enabled"] != enabled else "roles_settings"
        log_action(sid, "roles", action, actor=by, detail=str(len(rules)))
    return None


def role_member_metrics(server_id: int) -> list[list]:
    """Activity of each member of the server as the rules read it, without who they are (live preview of the Roles
    tab): [voice hours in total, voice hours over 30 days, messages, messages over 30 days, level on the server].
    Same reading as the bot (database/roles.go)."""
    from app.gamification import calculate_user_xp_and_level

    def load():
        sid = int(server_id)
        rows = _rows(
            "WITH m AS (SELECT user_id FROM guild_members WHERE server_id = %s), "
            "live AS (SELECT user_id, SUM(GREATEST(0, EXTRACT(EPOCH FROM (NOW() - joined_at))))::BIGINT AS sec FROM voice_sessions "
            "  WHERE server_id = %s AND left_at IS NULL AND NOT COALESCE(is_legacy, FALSE) GROUP BY user_id), "
            "v30 AS (SELECT user_id, SUM(COALESCE(duration_seconds, 0))::BIGINT AS sec FROM voice_sessions "
            "  WHERE server_id = %s AND left_at IS NOT NULL AND joined_at >= NOW() - INTERVAL '30 days' GROUP BY user_id), "
            "m30 AS (SELECT user_id, SUM(COALESCE(count, 1))::BIGINT AS n FROM message_events "
            "  WHERE server_id = %s AND created_at >= NOW() - INTERVAL '30 days' GROUP BY user_id) "
            "SELECT COALESCE(s.seconds, 0)::BIGINT + COALESCE(live.sec, 0), COALESCE(v30.sec, 0) + COALESCE(live.sec, 0), "
            "COALESCE(s.messages, 0)::BIGINT, COALESCE(m30.n, 0) "
            "FROM m LEFT JOIN stats s ON s.user_id = m.user_id AND s.server_id = %s "
            "LEFT JOIN live ON live.user_id = m.user_id LEFT JOIN v30 ON v30.user_id = m.user_id LEFT JOIN m30 ON m30.user_id = m.user_id",
            (sid, sid, sid, sid, sid))
        out = []
        for voice, voice30, msgs, msgs30 in rows:
            voice, voice30, msgs, msgs30 = int(voice or 0), int(voice30 or 0), int(msgs or 0), int(msgs30 or 0)
            level = calculate_user_xp_and_level(voice, msgs, 0)["level"]
            out.append([round(voice / 3600, 2), round(voice30 / 3600, 2), msgs, msgs30, level])
        return out
    return cache.get_or_set(("role_member_metrics", int(server_id)), 60, load)


def role_grant_counts(server_id: int) -> dict[str, int]:
    """{role id: members who have it from the bot} on this server."""
    return {str(role): int(n) for role, n in _rows(
        "SELECT role_id, COUNT(*) FROM role_grants WHERE server_id = %s GROUP BY role_id", (int(server_id),))}


# ------------------------------------------------------------------------------------------------ managers
def managers(server_id: int) -> list[dict]:
    """The owner's chosen managers, with their name on the server; those who left are flagged."""
    rows = _rows(
        "SELECT sm.user_id, sm.added_at, COALESCE(gm.username, u.username), gm.display_name, COALESCE(gm.avatar, u.avatar), gm.user_id IS NOT NULL "
        "FROM server_managers sm LEFT JOIN guild_members gm ON gm.server_id = sm.server_id AND gm.user_id = sm.user_id "
        "LEFT JOIN users u ON u.user_id = sm.user_id WHERE sm.server_id = %s ORDER BY sm.added_at", (int(server_id),))
    return [{"id": str(uid), "added_at": at, "name": name or f"#{uid}", "nickname": nick if nick and nick != name else None,
             "avatar": avatar, "member": bool(member)} for uid, at, name, nick, avatar, member in rows]


def search_members(server_id: int, query: str, limit: int = 8) -> list[dict]:
    """Members of the server by name (to pick a manager): the bot's live list."""
    q = (query or "").strip()[:40]
    if not q:
        return []
    rows = _rows(
        "SELECT user_id, display_name, username, avatar FROM guild_members gm WHERE server_id = %s "
        "AND (display_name ILIKE %s OR username ILIKE %s) "
        "AND NOT EXISTS (SELECT 1 FROM server_managers sm WHERE sm.server_id = gm.server_id AND sm.user_id = gm.user_id) "
        "AND gm.user_id <> COALESCE((SELECT owner_id FROM guild_meta WHERE server_id = gm.server_id), 0) "
        "ORDER BY display_name LIMIT %s",
        (int(server_id), f"%{q}%", f"%{q}%", limit))
    return [{"id": str(uid), "name": username or display or f"#{uid}", "nickname": display if display and display != username else "",
             "avatar": avatar} for uid, display, username, avatar in rows]


def add_manager(server_id: int, user_id: int, by: int) -> str | None:
    """None when added, else the reason: "self", "not_member", "full", "already"."""
    meta = guild_meta(server_id)
    if meta and meta["owner_id"] == int(user_id):
        return "self"
    if not is_member(user_id, server_id):
        return "not_member"
    current = managers(server_id)
    if any(m["id"] == str(user_id) for m in current):
        return "already"
    if len(current) >= MAX_MANAGERS:
        return "full"
    try:
        db.execute_sql("INSERT INTO server_managers (server_id, user_id, added_by, added_at) VALUES (%s, %s, %s, %s) "
                       "ON CONFLICT DO NOTHING", (int(server_id), int(user_id), int(by), _now()))
    except Exception:
        db.rollback()
        return "error"
    _forget_access(user_id)
    log_action(server_id, "general", "manager_added", actor=by, target=user_id)
    return None


def remove_manager(server_id: int, user_id: int, by: int) -> bool:
    try:
        cursor = db.execute_sql("DELETE FROM server_managers WHERE server_id = %s AND user_id = %s", (int(server_id), int(user_id)))
    except Exception:
        db.rollback()
        return False
    _forget_access(user_id)
    if cursor.rowcount:
        log_action(server_id, "general", "manager_removed", actor=by, target=user_id)
    return bool(cursor.rowcount)


def _forget_access(user_id: int) -> None:
    cache.delete(("managed_servers", int(user_id)))


# ------------------------------------------------------------------------------------------------ journal
def log_action(server_id: int, feature: str, action: str, actor: int | None = None, target: int | None = None,
               ok: bool = True, detail: str | None = None) -> None:
    try:
        db.execute_sql("INSERT INTO server_feature_log (server_id, created_at, feature, action, actor_id, target_id, ok, detail) "
                       "VALUES (%s, %s, %s, %s, %s, %s, %s, %s)",
                       (int(server_id), _now(), feature[:16], action[:32], actor, target, ok, (detail or None) and detail[:500]))
    except Exception:
        db.rollback()
        log.warning("Server journal line not written (%s %s)", feature, action)


def journal(server_id: int, limit: int = 200) -> list[dict]:
    """Last lines of the server's journal. People are named by their Discord username (unique, clear), with their
    nickname on this server as a tooltip."""
    rows = _rows(
        "SELECT l.created_at, l.feature, l.action, l.ok, l.detail, "
        "l.actor_id, COALESCE(ga.username, ua.username), ga.display_name, "
        "l.target_id, COALESCE(gt.username, ut.username), gt.display_name FROM server_feature_log l "
        "LEFT JOIN guild_members ga ON ga.server_id = l.server_id AND ga.user_id = l.actor_id "
        "LEFT JOIN users ua ON ua.user_id = l.actor_id "
        "LEFT JOIN guild_members gt ON gt.server_id = l.server_id AND gt.user_id = l.target_id "
        "LEFT JOIN users ut ON ut.user_id = l.target_id "
        "WHERE l.server_id = %s ORDER BY l.created_at DESC LIMIT %s", (int(server_id), limit))

    def person(uid, username, nickname):
        if not uid:
            return None
        return {"id": str(uid), "username": username or f"#{uid}", "nickname": nickname if nickname and nickname != username else None}

    return [{"at": at, "feature": feature, "action": action, "ok": ok, "detail": detail,
             "actor": person(actor, actor_user, actor_nick), "target": person(target, target_user, target_nick)}
            for at, feature, action, ok, detail, actor, actor_user, actor_nick, target, target_user, target_nick in rows]
