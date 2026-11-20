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
from datetime import datetime, timezone
from zoneinfo import available_timezones

from app.cache import cache
from app.database import create_tables, db

log = logging.getLogger(__name__)

DEFAULT_TIMEZONE = "Europe/Paris"
MAX_MANAGERS = 10
ACCESS_CACHE_SECONDS = 15  # owner and member checks: short, a change on Discord shows up quickly

TABLES = [
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
    ("view", 1 << 10), ("send", 1 << 11), ("embed", 1 << 14), ("attach", 1 << 15), ("history", 1 << 16), ("roles", 1 << 28),
]


def permission_texts(lang: str) -> dict[str, tuple[str, str]]:
    """{key: (name, what it is for)} of each permission the bot needs."""
    from app.i18n import tr
    return {
        "view": (tr("Voir les salons", "View channels", lang), tr("Pour lire les salons où il doit écrire.", "To see the channels it must write in.", lang)),
        "send": (tr("Envoyer des messages", "Send messages", lang), tr("Annonces de niveau et rapports.", "Level-up announcements and reports.", lang)),
        "embed": (tr("Intégrer des liens", "Embed links", lang), tr("Messages mis en forme.", "Formatted messages.", lang)),
        "attach": (tr("Joindre des fichiers", "Attach files", lang), tr("Cartes images des annonces et des rapports.", "Image cards of announcements and reports.", lang)),
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


def server_role(user_id: int | str | None, server_id: int) -> str | None:
    """"owner", "manager" or None for this visitor on this server."""
    if not user_id or not _enabled:
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
    if not user_id or not _enabled:
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


# ------------------------------------------------------------------------------------------------ managers
def managers(server_id: int) -> list[dict]:
    """The owner's chosen managers, with their name on the server; those who left are flagged."""
    rows = _rows(
        "SELECT sm.user_id, sm.added_at, COALESCE(gm.display_name, u.username), COALESCE(gm.avatar, u.avatar), gm.user_id IS NOT NULL "
        "FROM server_managers sm LEFT JOIN guild_members gm ON gm.server_id = sm.server_id AND gm.user_id = sm.user_id "
        "LEFT JOIN users u ON u.user_id = sm.user_id WHERE sm.server_id = %s ORDER BY sm.added_at", (int(server_id),))
    return [{"id": str(uid), "added_at": at, "name": name or f"#{uid}", "avatar": avatar, "member": bool(member)}
            for uid, at, name, avatar, member in rows]


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
    return [{"id": str(uid), "name": display or username or f"#{uid}", "username": username or "", "avatar": avatar}
            for uid, display, username, avatar in rows]


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
    rows = _rows(
        "SELECT l.created_at, l.feature, l.action, l.ok, l.detail, l.actor_id, COALESCE(ga.display_name, ua.username), "
        "l.target_id, COALESCE(gt.display_name, ut.username) FROM server_feature_log l "
        "LEFT JOIN guild_members ga ON ga.server_id = l.server_id AND ga.user_id = l.actor_id "
        "LEFT JOIN users ua ON ua.user_id = l.actor_id "
        "LEFT JOIN guild_members gt ON gt.server_id = l.server_id AND gt.user_id = l.target_id "
        "LEFT JOIN users ut ON ut.user_id = l.target_id "
        "WHERE l.server_id = %s ORDER BY l.created_at DESC LIMIT %s", (int(server_id), limit))
    return [{"at": at, "feature": feature, "action": action, "ok": ok, "detail": detail,
             "actor": actor_name or (f"#{actor}" if actor else None), "target": target_name or (f"#{target}" if target else None)}
            for at, feature, action, ok, detail, actor, actor_name, target, target_name in rows]
