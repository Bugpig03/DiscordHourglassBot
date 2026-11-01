"""Admin page: audience, Discord-linked accounts, profile customization, bot/database health, security journal
(admins only)."""

import json
import os
from collections import Counter
from datetime import date, datetime, timedelta, timezone

from flask import Blueprint, current_app, jsonify, render_template, request, url_for

from app.admin import admin_required
from app.analytics_tracking import flush as flush_audience
from app import security_log
from app.cache import cache
from app.database import db
from app.gamification import calculate_user_badges, normalize_badge_ids
from app.profile_gallery import BANNERS
from app.profile_records import RECORD_CATALOG
from app.profile_settings import BACKGROUND_COLORS, DEFAULT_ACCENT, HIDEABLE_BLOCKS, PALETTE, effective_banner_mode, normalize_accent
from app.i18n import current_lang, day_month, month_year

admin_bp = Blueprint("admin", __name__)

ADMIN_CACHE_SECONDS = 60
# Period of the whole admin page (lists, charts, totals), chosen in its top bar: days
ADMIN_PERIODS = (7, 30, 90)
DEFAULT_PERIOD = 30
PAGE_LABELS = {
    "home": ("Accueil", "Home"), "members": ("Membres", "Members"), "servers": ("Serveurs", "Servers"),
    "profile": ("Profils", "Profiles"), "server": ("Fiches serveur", "Server pages"), "graphs": ("Analyses", "Analytics"),
    "versus": ("Versus", "Versus"), "customize": ("Personnalisation", "Customization"), "help": ("Aide", "Help"),
    "privacy": ("Confidentialité", "Privacy"), "terms": ("Conditions", "Terms"), "other": ("Autres", "Other"),
}
SECURITY_ATTACK_KINDS = ("login_fail", "admin_denied", "csrf_fail", "rate_limited", "scan", "card_token_fail", "webhook_fail", "too_large")
# Tables above this size show PostgreSQL's estimate instead of an exact COUNT(*) (kept fast as the base grows)
EXACT_COUNT_MAX_BYTES = 512 * 1024 * 1024


@admin_bp.route("/admin", methods=["GET"])
@admin_required
def admin_page():
    return render_template("admin.html")


@admin_bp.route("/admin/data", methods=["GET"])
@admin_required
def admin_data():
    lang = current_lang()
    flush_audience(settle_all=False)  # include the last minute of this worker
    security_log.flush()
    days = request.args.get("days", type=int)
    days = days if days in ADMIN_PERIODS else DEFAULT_PERIOD
    data = dict(cache.get_or_set(("admin", lang, days), ADMIN_CACHE_SECONDS, lambda: compute_admin_data(lang, days)))
    # Security: never cached, and the configuration check-up reads this very request (proxy headers, HTTPS)
    data["security"] = compute_security(lang, days)
    return jsonify(data)


# ------------------------------------------------------------------------------
# Helpers
# ------------------------------------------------------------------------------

def _rows(sql: str, params=()) -> list[tuple]:
    try:
        return list(db.execute_sql(sql, params).fetchall())
    except Exception:
        db.rollback()
        return []


# Reclaimable space estimate: a row costs its data + 28 bytes (header and line pointer), pages are ~85 % full;
# an index entry ~40 bytes, at most ~70 % full. Above this much, the table is worth a VACUUM FULL.
ROW_OVERHEAD_BYTES = 28
INDEX_ENTRY_BYTES = 40
RECLAIM_MIN_BYTES = 1024 * 1024


def _table_sizes() -> list[tuple]:
    """(name, rows, bytes, reclaimable bytes) of every table of the database, biggest first.

    Row counts are exact (COUNT(*)) up to EXACT_COUNT_MAX_BYTES: the planner estimates read 0 or -1 for tables
    never analyzed or restored from a dump. Reclaimable space is what the table and its indexes take beyond what
    their rows need: space left by deleted rows, that PostgreSQL keeps for the table until a VACUUM FULL (None
    when the table is too big to measure quickly).
    """
    out = []
    for name, estimate, size, heap, index_size, index_count in _rows(
            "SELECT c.relname, GREATEST(c.reltuples, 0)::bigint, pg_total_relation_size(c.oid), pg_relation_size(c.oid), "
            "pg_indexes_size(c.oid), (SELECT COUNT(*) FROM pg_index i WHERE i.indrelid = c.oid) FROM pg_class c "
            "JOIN pg_namespace n ON n.oid = c.relnamespace WHERE c.relkind = 'r' AND n.nspname = 'public' ORDER BY 3 DESC"):
        rows, reclaimable = estimate, None
        if size <= EXACT_COUNT_MAX_BYTES:
            quoted = '"' + name.replace('"', '""') + '"'  # names come from the catalog
            measured = _rows(f"SELECT COUNT(*), COALESCE(SUM(pg_column_size(t.*)), 0) FROM {quoted} t")
            if measured:
                rows, data_bytes = int(measured[0][0]), int(measured[0][1])
                needed_heap = (data_bytes + rows * ROW_OVERHEAD_BYTES) / 0.85 + 8192
                needed_index = (rows * INDEX_ENTRY_BYTES / 0.7 + 16384) * int(index_count)
                reclaimable = int(max(0, heap - needed_heap) + max(0, index_size - needed_index))
        out.append((name, rows, size, reclaimable))
    return out


def _one(sql: str, params=(), default=0):
    rows = _rows(sql, params)
    return rows[0][0] if rows and rows[0][0] is not None else default


def _days(n: int) -> list[date]:
    today = datetime.now(timezone.utc).date()
    return [today - timedelta(days=n - 1 - i) for i in range(n)]


def _day_label(d: date, lang: str) -> str:
    return day_month(d.day, d.month, lang)


def _series(rows: list[tuple], days: list[date]) -> list[int]:
    by_day = {r[0]: int(r[1] or 0) for r in rows}
    return [by_day.get(d, 0) for d in days]


def _delta(current: float, previous: float) -> float | None:
    return round((current - previous) / previous * 100, 1) if previous else None


def _names(kind: str, ids: list[str]) -> dict[str, dict]:
    """Display name + link for profile identifiers (id or username) and server ids."""
    out = {}
    if kind == "server":
        numeric = [int(i) for i in ids if i.isdigit()]
        if numeric:
            for sid, name, avatar in _rows("SELECT server_id, servername, avatar FROM servers WHERE server_id = ANY(%s)", (numeric,)):
                out[str(sid)] = {"name": name or str(sid), "avatar": avatar, "url": url_for("server_profile.server", server_id=sid)}
        return out
    numeric = [int(i) for i in ids if i.isdigit()]
    names = [i for i in ids if not i.isdigit()]
    if numeric:
        for uid, name, avatar in _rows("SELECT user_id, username, avatar FROM users WHERE user_id = ANY(%s)", (numeric,)):
            out[str(uid)] = {"name": name or str(uid), "avatar": avatar, "url": url_for("user_profile.profile", username=uid)}
    if names:
        for uid, name, avatar in _rows("SELECT user_id, username, avatar FROM users WHERE LOWER(username) = ANY(%s)", (names,)):
            out.setdefault(name.lower(), {"name": name, "avatar": avatar, "url": url_for("user_profile.profile", username=uid)})
    return out


# ------------------------------------------------------------------------------
# Data
# ------------------------------------------------------------------------------

def compute_admin_data(lang: str = "fr", days: int = DEFAULT_PERIOD) -> dict:
    """Everything the admin page shows over the last `days` days (and the previous `days` for the comparisons)."""
    fr = lang == "fr"
    today = datetime.now(timezone.utc).date()
    win, span = _days(days), _days(days * 2)

    # ---------------- Traffic ----------------
    views = _rows("SELECT day, SUM(views) FROM web_pageviews_daily WHERE day >= %s GROUP BY day", (span[0],))
    uniques = _rows("SELECT day, COUNT(*) FROM web_visitors_daily WHERE day >= %s GROUP BY day", (span[0],))
    views_s, uniques_s = _series(views, span), _series(uniques, span)

    def period(series, n, offset=0):
        end = len(series) - offset
        return sum(series[max(0, end - n):end])

    pages = _rows("SELECT page_key, SUM(views) FROM web_pageviews_daily WHERE day >= %s GROUP BY page_key ORDER BY 2 DESC", (win[0],))
    referrers = _rows("SELECT domain, SUM(views) FROM web_referrers_daily WHERE day >= %s GROUP BY domain ORDER BY 2 DESC LIMIT 50", (win[0],))
    hourly = dict(_rows("SELECT hour, SUM(views) FROM web_hourly_views WHERE day >= %s GROUP BY hour", (win[0],)))
    devices = _rows("SELECT is_mobile, COUNT(*) FROM web_visitors_daily WHERE day >= %s GROUP BY is_mobile", (win[0],))
    langs = _rows("SELECT lang, COUNT(*) FROM web_visitors_daily WHERE day >= %s GROUP BY lang", (win[0],))
    searches = _rows("SELECT term, SUM(hits) FROM web_searches_daily WHERE day >= %s GROUP BY term ORDER BY 2 DESC LIMIT 100", (win[0],))

    def top_entities(kind):
        # Rows recorded before v3.16.0 may hold a username or an id for the same member: merge them by target
        rows = _rows("SELECT entity_id, SUM(views) FROM web_entity_views_daily WHERE kind = %s AND day >= %s GROUP BY entity_id ORDER BY 2 DESC LIMIT 200", (kind, win[0]))
        names = _names(kind, [r[0] for r in rows])
        merged: dict[str, dict] = {}
        for entity_id, views in rows:
            info = names.get(entity_id, {"name": entity_id, "avatar": None, "url": None})
            key = info.get("url") or f"raw:{entity_id}"
            item = merged.setdefault(key, {**info, "value": 0})
            item["value"] += int(views)
        return sorted(merged.values(), key=lambda x: -x["value"])[:50]

    device_counts = {bool(k): int(v) for k, v in devices}
    traffic = {
        "labels": [_day_label(d, lang) for d in win],
        "views": views_s[-days:],
        "uniques": uniques_s[-days:],
        "pages": [{"name": PAGE_LABELS.get(k, (k, k))[0 if fr else 1], "value": int(v)} for k, v in pages],
        "top_profiles": top_entities("profile"),
        "top_servers": top_entities("server"),
        "referrers": [{"name": ("Accès direct" if fr else "Direct") if k == "direct" else ("Discord" if k == "discord" else k), "value": int(v)} for k, v in referrers],
        "devices": {"mobile": device_counts.get(True, 0), "desktop": device_counts.get(False, 0)},
        "langs": {k: int(v) for k, v in langs},
        "hourly": [int(hourly.get(h, 0)) for h in range(24)],
        "searches": [{"name": t, "value": int(n)} for t, n in searches],
    }

    # ---------------- Accounts ----------------
    accounts_total = int(_one("SELECT COUNT(*) FROM web_accounts"))
    members_total = int(_one("SELECT COUNT(*) FROM users"))
    new_week = int(_one("SELECT COUNT(*) FROM web_accounts WHERE first_login_at >= %s", (datetime.utcnow() - timedelta(days=7),)))
    weeks = _rows(
        "SELECT DATE_TRUNC('week', first_login_at)::date, COUNT(*) FROM web_accounts "
        "WHERE first_login_at >= %s GROUP BY 1 ORDER BY 1", (datetime.utcnow() - timedelta(weeks=12),))
    active_daily = _rows("SELECT day, COUNT(*) FROM web_logins_daily WHERE day >= %s GROUP BY day", (win[0],))
    active7 = int(_one("SELECT COUNT(DISTINCT user_id) FROM web_logins_daily WHERE day >= %s", (today - timedelta(days=6),)))
    active30 = int(_one("SELECT COUNT(DISTINCT user_id) FROM web_logins_daily WHERE day >= %s", (win[0],)))
    recent = _rows(
        "SELECT a.user_id, COALESCE(u.username, a.username), COALESCE(u.avatar, a.avatar), a.last_login_at, a.login_count, "
        "a.first_login_at FROM web_accounts a "
        "LEFT JOIN users u ON u.user_id = a.user_id ORDER BY a.last_login_at DESC LIMIT 100")
    accounts = {
        "total": accounts_total,
        "members_total": members_total,
        "linked_percent": round(accounts_total / members_total * 100, 1) if members_total else 0,
        "new_week": new_week,
        "active7": active7,
        "active30": active30,
        "weeks": {"labels": [_day_label(w, lang) for w, _ in weeks], "values": [int(n) for _, n in weeks]},
        "active_daily": {"labels": [_day_label(d, lang) for d in win], "values": _series(active_daily, win)},
        "recent": [
            {"name": name or str(uid), "avatar": avatar, "url": url_for("user_profile.profile", username=uid),
             "last": last.isoformat(timespec="minutes") if last else None, "count": int(count),
             "first": first.isoformat(timespec="minutes") if first else None}
            for uid, name, avatar, last, count, first in recent
        ],
    }

    # ---------------- Customization ----------------
    settings_rows = _rows(
        "SELECT accent_color, banner_mode, banner_image, background_color, favorite_server_id, featured_badges, pinned_records, layout "
        "FROM user_profile_settings")
    accent_c, banner_mode_c, banner_c, bg_c, badge_c, record_c, hidden_c = (Counter() for _ in range(7))
    customized = private = favorite = 0
    for accent, mode, banner, bg, fav, featured, pinned, layout in settings_rows:
        try:
            featured, pinned, layout = json.loads(featured or "[]"), json.loads(pinned or "[]"), json.loads(layout or "{}")
        except ValueError:
            featured, pinned, layout = [], [], {}
        hidden = layout.get("hidden") or []
        is_private = bool(layout.get("private"))
        mode = effective_banner_mode(mode, banner)  # no banner unless a gallery picture was picked
        changed = (accent not in (None, DEFAULT_ACCENT) or mode == "image" or bg or fav or featured or pinned or hidden or is_private)
        customized += bool(changed)
        private += is_private
        favorite += bool(fav)
        accent_c[normalize_accent(accent)] += 1
        banner_mode_c[mode] += 1
        if mode == "image":
            banner_c[banner] += 1
        if bg:
            bg_c[bg] += 1
        badge_c.update(normalize_badge_ids(featured))
        record_c.update(pinned)
        hidden_c.update(hidden)
    palette = {k: (h, f, e) for k, h, f, e in PALETTE}
    badge_names = {b["id"]: b["name"] for b in calculate_user_badges({}, lang=lang)}
    mode_labels = {"image": ("Galerie", "Gallery"), "none": ("Aucune", "None")}
    bg_colors = {k: (h, f, e) for k, h, f, e in BACKGROUND_COLORS}
    pick = (lambda pair: pair[0] if fr else pair[1])
    customization = {
        "rows": len(settings_rows),
        "customized": customized,
        "customized_percent": round(customized / accounts_total * 100, 1) if accounts_total else 0,
        "private": private,
        "favorite": favorite,
        "accents": [{"name": pick(palette[k][1:]) if k in palette else ("Couleur Discord" if fr else "Discord color"),
                     "color": palette[k][0] if k in palette else "#5865f2", "value": v} for k, v in accent_c.most_common()],
        "banner_modes": [{"name": pick(mode_labels.get(k, (k, k))), "value": v} for k, v in banner_mode_c.most_common()],
        "banners": [{"name": pick(BANNERS.get(k, (k, k))), "value": v} for k, v in banner_c.most_common()],
        "backgrounds": [{"name": pick(bg_colors[k][1:]), "color": bg_colors[k][0], "value": v} for k, v in bg_c.most_common(12) if k in bg_colors],
        "badges": [{"name": badge_names.get(k, k), "value": v} for k, v in badge_c.most_common()],
        "records": [{"name": pick(RECORD_CATALOG[k][1:]) if k in RECORD_CATALOG else k, "value": v} for k, v in record_c.most_common()],
        "hidden": [{"name": pick(HIDEABLE_BLOCKS.get(k, (k, k))), "value": v} for k, v in hidden_c.most_common()],
    }

    # ---------------- Bot & database ----------------
    month_start = (today.replace(day=1) - timedelta(days=330)).replace(day=1)
    # Arrival of a server: first_tracked_at or its first stats row, whichever is older (the column was added in
    # October 2026 with DEFAULT CURRENT_TIMESTAMP: servers known before carry that day)
    arrived_sql = ("SELECT s.server_id, s.servername, s.avatar, LEAST(s.first_tracked_at, f.first) AS arrived, s.left_at FROM servers s"
                   " LEFT JOIN (SELECT server_id, MIN(date_creation) AS first FROM stats GROUP BY server_id) f ON f.server_id = s.server_id")
    joins = dict(_rows(f"SELECT DATE_TRUNC('month', arrived)::date, COUNT(*) FROM ({arrived_sql}) a WHERE arrived >= %s GROUP BY 1", (month_start,)))
    leaves = dict(_rows("SELECT DATE_TRUNC('month', left_at)::date, COUNT(*) FROM servers WHERE left_at >= %s GROUP BY 1", (month_start,)))
    months = []
    m = month_start
    while m <= today:
        months.append(m)
        m = (m + timedelta(days=32)).replace(day=1)
    last_presence = _one("SELECT MAX(recorded_at) FROM presence_history", default=None)
    last_heartbeat = _one("SELECT MAX(last_heartbeat) FROM voice_sessions WHERE left_at IS NULL", default=None)
    now_naive = datetime.utcnow()
    presence_age = round((now_naive - last_presence).total_seconds() / 60) if last_presence else None
    sizes = _table_sizes()
    # Latest arrivals: a member arrives with their first stats row (first activity seen on any server)
    member_rows = _rows(
        "SELECT f.user_id, f.first_seen, u.username, u.avatar, sv.server_id, sv.servername FROM ("
        " SELECT DISTINCT ON (user_id) user_id, server_id, date_creation AS first_seen FROM stats"
        " WHERE date_creation IS NOT NULL ORDER BY user_id, date_creation) f"
        " LEFT JOIN users u ON u.user_id = f.user_id LEFT JOIN servers sv ON sv.server_id = f.server_id"
        " ORDER BY f.first_seen DESC LIMIT 30")
    server_rows = _rows(f"SELECT * FROM ({arrived_sql}) a WHERE arrived IS NOT NULL ORDER BY arrived DESC LIMIT 30")
    arrivals = {
        "members": [{
            "name": name or str(uid), "avatar": avatar, "url": url_for("user_profile.profile", username=uid),
            "at": first.isoformat(timespec="minutes"),
            "server": srv_name or (str(srv_id) if srv_id else None),
            "server_url": url_for("server_profile.server", server_id=srv_id) if srv_id else None,
        } for uid, first, name, avatar, srv_id, srv_name in member_rows],
        "servers": [{
            "name": name or str(sid), "avatar": avatar, "url": url_for("server_profile.server", server_id=sid),
            "at": first.isoformat(timespec="minutes"), "left": left.isoformat(timespec="minutes") if left else None,
        } for sid, name, avatar, first, left in server_rows],
    }

    # Unique people present on the servers right now (bot v3.3.0 snapshot, every 15 min), active or not
    snap = _rows("SELECT recorded_at, unique_members, unique_online, memberships, servers, known_members "
                 "FROM bot_member_snapshots ORDER BY recorded_at DESC LIMIT 1")
    snap_days = _rows("SELECT recorded_at::date, MAX(unique_members), MAX(known_members) FROM bot_member_snapshots "
                      "WHERE recorded_at >= %s GROUP BY 1 ORDER BY 1", (win[0],))
    audience = None
    if snap:
        at, unique, online, memberships, servers_listed, known = snap[0]
        audience = {
            "at": at.isoformat(timespec="minutes"), "unique": int(unique), "online": int(online),
            "memberships": int(memberships), "servers": int(servers_listed), "known": int(known),
            "silent": max(0, int(unique) - int(known)),
            "silent_percent": round((int(unique) - int(known)) / int(unique) * 100, 1) if unique else 0,
            "per_member": round(int(memberships) / int(unique), 2) if unique else 0,
            # Only the days with a snapshot (no fake zeros before the bot started counting)
            "labels": [_day_label(r[0], lang) for r in snap_days],
            "unique_daily": [int(r[1]) for r in snap_days],
            "known_daily": [int(r[2]) for r in snap_days],
        }

    bot = {
        "arrivals": arrivals,
        "audience": audience,
        "servers_total": int(_one("SELECT COUNT(*) FROM servers")),
        "servers_present": int(_one("SELECT COUNT(*) FROM servers WHERE is_bot_present")),
        "servers_left": int(_one("SELECT COUNT(*) FROM servers WHERE NOT is_bot_present")),
        "servers_active30": int(_one(
            "SELECT COUNT(DISTINCT server_id) FROM (SELECT server_id FROM voice_sessions WHERE joined_at >= %s "
            "UNION SELECT server_id FROM message_events WHERE created_at >= %s) t", (now_naive - timedelta(days=30),) * 2)),
        "members_total": members_total,
        "voice_now": int(_one("SELECT COUNT(*) FROM voice_sessions WHERE left_at IS NULL")),
        "messages_24h": int(_one("SELECT COALESCE(SUM(count), 0) FROM message_events WHERE created_at >= %s", (now_naive - timedelta(hours=24),))),
        "orphans": int(_one("SELECT COUNT(*) FROM voice_sessions WHERE left_at IS NULL AND joined_at < %s", (now_naive - timedelta(hours=24),))),
        "last_presence": last_presence.isoformat(timespec="minutes") if last_presence else None,
        "presence_age_min": presence_age,
        "bot_online": presence_age is not None and presence_age <= 30,
        "last_heartbeat": last_heartbeat.isoformat(timespec="minutes") if last_heartbeat else None,
        "months": {"labels": [month_year(m.month, m.year, lang) for m in months],
                   "joins": [int(joins.get(m, 0)) for m in months], "leaves": [int(leaves.get(m, 0)) for m in months]},
        "tables": [{"name": n, "rows": int(r), "mb": round(b / 1048576, 1),
                    "reclaim_mb": round(f / 1048576, 1) if f is not None and f >= RECLAIM_MIN_BYTES else 0}
                   for n, r, b, f in sizes],
        "db_mb": round(int(_one("SELECT pg_database_size(current_database())")) / 1048576, 1),
    }

    # ---------------- top.gg votes (webhook and hourly catch-up, web v3.32.0) ----------------
    vote_daily = _rows("SELECT created_at::date, COUNT(*) FROM topgg_votes WHERE created_at >= %s GROUP BY 1", (win[0],))
    vote_top = _rows(
        "SELECT v.user_id, COALESCE(u.username, a.username), COALESCE(u.avatar, a.avatar), COUNT(*) FROM topgg_votes v "
        "LEFT JOIN users u ON u.user_id = v.user_id LEFT JOIN web_accounts a ON a.user_id = v.user_id "
        "WHERE v.created_at >= %s GROUP BY v.user_id, 2, 3 ORDER BY 4 DESC LIMIT 50", (win[0],))
    month_start = today.replace(day=1)
    votes = {
        "total": int(_one("SELECT COUNT(*) FROM topgg_votes")),
        "period": sum(int(n) for _, n in vote_daily),
        "voters": int(_one("SELECT COUNT(DISTINCT user_id) FROM topgg_votes WHERE created_at >= %s", (win[0],))),
        "month": int(_one("SELECT COUNT(*) FROM topgg_votes WHERE created_at >= %s", (month_start,))),
        "active": int(_one("SELECT COUNT(DISTINCT user_id) FROM topgg_votes WHERE expires_at > %s", (datetime.utcnow(),))),
        "labels": [_day_label(d, lang) for d in win],
        "daily": _series(vote_daily, win),
        "top": [{"name": name or str(uid), "avatar": avatar, "url": url_for("user_profile.profile", username=uid), "value": int(n)}
                for uid, name, avatar, n in vote_top],
        "webhook_ready": bool(os.environ.get("TOPGG_WEBHOOK_SECRET")),
        "api_ready": bool(os.environ.get("TOPGG_TOKEN")),
    }

    # ---------------- Site health ----------------
    status_rows = _rows("SELECT day, status, SUM(hits) FROM web_status_daily WHERE day >= %s GROUP BY day, status", (win[0],))
    by_status = {s: {} for s in (404, 429, 500)}
    for day, status, hits in status_rows:
        by_status.setdefault(int(status), {})[day] = int(hits)
    top_404 = _rows("SELECT path_key, SUM(hits) FROM web_status_daily WHERE status = 404 AND day >= %s GROUP BY path_key ORDER BY 2 DESC LIMIT 50", (win[0],))
    from app.routes.graphs import LAST_REFRESH
    from app import config as app_config
    health = {
        "labels": [_day_label(d, lang) for d in win],
        "s404": [by_status[404].get(d, 0) for d in win],
        "s429": [by_status[429].get(d, 0) for d in win],
        "s500": [by_status[500].get(d, 0) for d in win],
        "top_404": [{"name": p, "value": int(n)} for p, n in top_404],
        "analytics_refresh": dict(LAST_REFRESH),
        "session_key_source": app_config.SECRET_KEY_SOURCE,
    }

    # ---------------- Bot commands (table written by the bot since bot v3.1.0) ----------------
    cmd_daily = _rows("SELECT created_at::date, COUNT(*) FROM bot_command_events WHERE created_at >= %s GROUP BY 1", (win[0],))
    cmd_top = _rows(
        "SELECT command, COUNT(*), SUM(CASE WHEN success THEN 0 ELSE 1 END), "
        "ROUND(AVG(duration_ms)), PERCENTILE_CONT(0.95) WITHIN GROUP (ORDER BY duration_ms) "
        "FROM bot_command_events WHERE created_at >= %s GROUP BY command ORDER BY 2 DESC", (win[0],))
    cmd_servers = _rows(
        "SELECT e.server_id, s.servername, s.avatar, COUNT(*) FROM bot_command_events e LEFT JOIN servers s ON s.server_id = e.server_id "
        "WHERE e.created_at >= %s AND e.server_id IS NOT NULL GROUP BY e.server_id, s.servername, s.avatar ORDER BY 4 DESC LIMIT 50", (win[0],))
    cmd_options = _rows(
        "SELECT options, COUNT(*) FROM bot_command_events WHERE created_at >= %s AND options <> '' GROUP BY options ORDER BY 2 DESC LIMIT 50", (win[0],))
    cmd_dm = int(_one("SELECT COUNT(*) FROM bot_command_events WHERE created_at >= %s AND server_id IS NULL", (win[0],)))
    cmd_total = sum(int(r[1]) for r in cmd_top)
    cmd_failed = sum(int(r[2] or 0) for r in cmd_top)
    dm_label = "refusée en DM" if fr else "refused in DM"
    commands = {
        "total": cmd_total,
        "today": _series(cmd_daily, win)[-1],
        "failed": cmd_failed,
        "failed_percent": round(cmd_failed / cmd_total * 100, 1) if cmd_total else 0,
        "dm": cmd_dm,
        "labels": [_day_label(d, lang) for d in win],
        "daily": _series(cmd_daily, win),
        "top": [{"name": f"/{c}", "value": int(n)} for c, n, _, _, _ in cmd_top],
        "perf": [{"name": f"/{c}", "count": int(n), "failed": int(f or 0), "avg_ms": int(a or 0), "p95_ms": int(p or 0)} for c, n, f, a, p in cmd_top],
        "servers": [{"name": name or str(sid), "avatar": avatar, "url": url_for("server_profile.server", server_id=sid), "value": int(n)}
                    for sid, name, avatar, n in cmd_servers],
        "options": [{"name": o.replace("dm_refused", dm_label), "value": int(n)} for o, n in cmd_options],
    }

    return {
        "commands": commands,
        "overview": {
            "days": days,
            "views_today": views_s[-1], "views": period(views_s, days), "views_prev": period(views_s, days, days),
            "uniques_today": uniques_s[-1], "uniques_avg": round(period(uniques_s, days) / days, 1),
            "uniques_delta": _delta(period(uniques_s, days), period(uniques_s, days, days)),
            "accounts": accounts_total, "accounts_new_week": new_week,
            "customized": customized, "customized_percent": customization["customized_percent"],
            "servers_present": bot["servers_present"], "servers_active30": bot["servers_active30"],
            "delta": _delta(period(views_s, days), period(views_s, days, days)),
            "tracking_since": str(_one("SELECT MIN(day) FROM web_pageviews_daily", default="")) or None,
        },
        "traffic": traffic,
        "accounts": accounts,
        "customization": customization,
        "bot": bot,
        "votes": votes,
        "health": health,
        "generated_at": datetime.utcnow().isoformat(timespec="seconds"),
    }


# ------------------------------------------------------------------------------
# Security journal and configuration check-up
# ------------------------------------------------------------------------------

def _config_checkup(fr: bool) -> list[dict]:
    """Settings that matter for security, green or red, read from the running app and this request.

    Each line says what was found: why it is fine when green, what goes wrong and what to set when red.
    """
    from app import config as app_config
    from app.config import Config
    from app.security import HSTS_FROM_PROXY, client_ip
    t = (lambda a, b: a if fr else b)
    source = app_config.SECRET_KEY_SOURCE
    key_text = {
        "env": (t("Variable SECRET_KEY : stable entre les mises à jour.", "SECRET_KEY variable: stable across updates.")),
        "database": (t("Enregistrée en base : stable entre les mises à jour.", "Stored in the database: stable across updates.")),
        "discord": (t("Dérivée du secret Discord : stable tant que le secret ne change pas.", "Derived from the Discord secret: stable as long as the secret does not change.")),
        "file": (t("Fichier du conteneur : perdue à chaque mise à jour, les membres sont déconnectés. Définir SECRET_KEY.",
                   "Container file: lost on every update, members are logged out. Set SECRET_KEY.")),
        "random": (t("Aléatoire : change à chaque démarrage, les membres sont déconnectés. Définir SECRET_KEY.",
                     "Random: changes on every start, members are logged out. Set SECRET_KEY.")),
    }.get(source, source)
    seen_ip = security_log.short_ip(client_ip()) or t("inconnue", "unknown")
    proxy_ip = bool(request.headers.get("X-Real-IP") or request.headers.get("X-Forwarded-For"))
    ip_ok = proxy_ip or not request.remote_addr or client_ip() == request.remote_addr
    csp_report_only = os.environ.get("CSP_REPORT_ONLY", "false").lower() in ("1", "true", "yes")
    admins = len(Config.ADMIN_USER_IDS)
    # (label, ok, text when ok, text when not)
    checks = [
        (t("Clé de session", "Session key"), source in ("env", "discord", "database"), key_text, key_text),
        (t("HTTPS", "HTTPS"), request.is_secure,
         t("Le site est servi en HTTPS.", "The site is served over HTTPS."),
         t("Page reçue en HTTP : le proxy doit envoyer X-Forwarded-Proto: https.", "Page received over HTTP: the proxy must send X-Forwarded-Proto: https.")),
        (t("HSTS", "HSTS"), True,
         t("Envoyé par le proxy (HSTS_FROM_PROXY).", "Sent by the proxy (HSTS_FROM_PROXY).") if HSTS_FROM_PROXY else
         t("Envoyé par le site (6 mois). Si le proxy en envoie aussi un, définir HSTS_FROM_PROXY=true.",
           "Sent by the site (6 months). If the proxy sends one too, set HSTS_FROM_PROXY=true."), ""),
        (t("Cookie de session", "Session cookie"), bool(Config.SESSION_COOKIE_SECURE),
         t("Envoyé uniquement en HTTPS.", "Only sent over HTTPS."),
         t("Envoyé aussi en HTTP : retirer SESSION_COOKIE_SECURE=false.", "Also sent over HTTP: remove SESSION_COOKIE_SECURE=false.")),
        (t("Politique de sécurité (CSP)", "Content Security Policy"), not csp_report_only,
         t("Appliquée : les scripts non autorisés sont bloqués.", "Enforced: unauthorized scripts are blocked."),
         t("En simple rapport : rien n'est bloqué. Retirer CSP_REPORT_ONLY.", "Report-only: nothing is blocked. Remove CSP_REPORT_ONLY.")),
        (t("Mode debug", "Debug mode"), not current_app.debug,
         t("Désactivé.", "Off."),
         t("Activé : les erreurs affichent le code. Retirer FLASK_DEBUG.", "On: errors show the code. Remove FLASK_DEBUG.")),
        (t("Mot de passe de la base", "Database password"), Config.DB_PASSWORD not in ("", "admin", "postgres"),
         t("Personnalisé.", "Custom."),
         t("Valeur par défaut : changer POSTGRESQL_PASSWORD.", "Default value: change POSTGRESQL_PASSWORD.")),
        (t("Cartes du bot", "Bot cards"), bool(Config.CARD_TOKEN),
         t("Jeton défini : seul le bot peut demander les cartes.", "Token set: only the bot can request the cards."),
         t("CARD_TOKEN absent : le bot ne peut pas obtenir ses cartes.", "CARD_TOKEN missing: the bot cannot get its cards.")),
        (t("Connexion Discord", "Discord login"), bool(Config.DISCORD_CLIENT_SECRET),
         t("Par code : le jeton Discord ne passe jamais par le navigateur.", "By code: the Discord token never goes through the browser."),
         t("Mode implicite, moins sûr : définir DISCORD_CLIENT_SECRET.", "Implicit mode, less safe: set DISCORD_CLIENT_SECRET.")),
        (t("IP des visiteurs", "Visitor IP"), ip_ok,
         t(f"Transmise par le proxy (vue ici : {seen_ip}).", f"Passed on by the proxy (seen here: {seen_ip})."),
         t("Le proxy n'envoie pas X-Real-IP : tous les visiteurs ont la même IP pour les limites.",
           "The proxy sends no X-Real-IP: every visitor shares one IP for the limits.")),
        (t("Journal de sécurité", "Security journal"), security_log._enabled,
         t("Actif, conservé 90 jours.", "On, kept 90 days."),
         t("Table web_security_events indisponible : voir les logs du site.", "web_security_events table unavailable: see the site logs.")),
        (t("Comptes admin", "Admin accounts"), 0 < admins <= 3,
         t(f"{admins} compte(s) dans ADMIN_USER_IDS.", f"{admins} account(s) in ADMIN_USER_IDS."),
         t(f"{admins} compte(s) dans ADMIN_USER_IDS : en garder entre 1 et 3.", f"{admins} account(s) in ADMIN_USER_IDS: keep 1 to 3.")),
    ]
    return [{"label": label, "ok": bool(ok), "detail": good if ok else bad} for label, ok, good, bad in checks]


def compute_security(lang: str = "fr", days: int = DEFAULT_PERIOD) -> dict:
    fr = lang == "fr"
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    win = _days(days)
    labels = {k: (fr_l if fr else en_l) for k, (fr_l, en_l, _) in security_log.KINDS.items()}
    severity = {k: sev for k, (_, _, sev) in security_log.KINDS.items()}

    def totals(since):
        return {k: int(n) for k, n in _rows("SELECT kind, SUM(hits) FROM web_security_events WHERE at >= %s GROUP BY kind", (since,))}

    daily = _rows("SELECT at::date, kind, SUM(hits) FROM web_security_events WHERE at >= %s GROUP BY 1, 2", (win[0],))
    by_kind = {}
    for day, kind, n in daily:
        by_kind.setdefault(kind, {})[day] = int(n)
    attack = SECURITY_ATTACK_KINDS + ("csp_violation", "server_error")
    since7 = now - timedelta(days=7)
    top_ips = _rows(
        "SELECT ip, SUM(hits), STRING_AGG(DISTINCT kind, ',') FROM web_security_events "
        "WHERE at >= %s AND ip IS NOT NULL AND kind = ANY(%s) GROUP BY ip ORDER BY 2 DESC LIMIT 40", (since7, list(attack)))
    top_paths = _rows(
        "SELECT path, SUM(hits) FROM web_security_events WHERE at >= %s AND kind = ANY(%s) AND path <> '' "
        "GROUP BY path ORDER BY 2 DESC LIMIT 40", (since7, list(attack)))
    names = "LEFT JOIN web_accounts a ON a.user_id = e.user_id LEFT JOIN users u ON u.user_id = e.user_id"
    recent = _rows(
        f"SELECT e.at, e.kind, e.ip, e.path, e.user_id, COALESCE(u.username, a.username), e.detail, e.hits "
        f"FROM web_security_events e {names} ORDER BY e.at DESC, e.id DESC LIMIT 300")
    admin_log = _rows(
        f"SELECT e.at, e.kind, e.ip, e.user_id, COALESCE(u.username, a.username), e.detail, e.hits FROM web_security_events e {names} "
        "WHERE e.kind IN ('admin_access', 'admin_denied') ORDER BY e.at DESC, e.id DESC LIMIT 60")

    def event(row):
        at, kind, ip, path, uid, name, detail, hits = row
        return {"at": at.isoformat(timespec="seconds"), "kind": kind, "label": labels.get(kind, kind), "severity": severity.get(kind, "info"),
                "ip": ip, "path": path, "user": name or (str(uid) if uid else None),
                "user_url": url_for("user_profile.profile", username=uid) if uid else None, "detail": detail, "hits": int(hits)}

    return {
        "enabled": security_log._enabled,
        "kinds": [{"key": k, "label": labels[k], "severity": severity[k]} for k in security_log.KINDS],
        "totals_24h": totals(now - timedelta(hours=24)),
        "totals_7d": totals(since7),
        "labels": [_day_label(d, lang) for d in win],
        "daily": {k: [v.get(d, 0) for d in win] for k, v in by_kind.items()},
        "top_ips": [{"name": f"{ip} · " + ", ".join(labels.get(k, k) for k in (kinds or "").split(",") if k), "value": int(n)}
                    for ip, n, kinds in top_ips],
        "top_paths": [{"name": p, "value": int(n)} for p, n in top_paths],
        "recent": [event(r) for r in recent],
        "admin_log": [event((at, kind, ip, "", uid, name, detail, hits)) for at, kind, ip, uid, name, detail, hits in admin_log],
        "checkup": _config_checkup(fr),
        "retention_days": security_log.RETENTION_DAYS,
    }
