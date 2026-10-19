"""Admin page: audience, Discord-linked accounts, profile customization, bot/database health (admins only)."""

import json
from collections import Counter
from datetime import date, datetime, timedelta, timezone

from flask import Blueprint, jsonify, render_template, request, url_for

from app.admin import admin_required
from app.analytics_tracking import flush as flush_audience
from app.cache import cache
from app.database import db
from app.functions import get_month_abbr
from app.gamification import calculate_user_badges
from app.profile_gallery import BANNERS
from app.profile_records import RECORD_CATALOG
from app.profile_settings import BACKGROUND_COLORS, HIDEABLE_BLOCKS, PALETTE, effective_banner_mode

admin_bp = Blueprint("admin", __name__)

ADMIN_CACHE_SECONDS = 60
PAGE_LABELS = {
    "home": ("Accueil", "Home"), "members": ("Membres", "Members"), "servers": ("Serveurs", "Servers"),
    "profile": ("Profils", "Profiles"), "server": ("Fiches serveur", "Server pages"), "graphs": ("Analyses", "Analytics"),
    "versus": ("Versus", "Versus"), "customize": ("Personnalisation", "Customization"), "help": ("Aide", "Help"),
    "privacy": ("Confidentialité", "Privacy"), "terms": ("Conditions", "Terms"), "other": ("Autres", "Other"),
}
DB_TABLES = ["voice_sessions", "message_events", "historical_stats", "stats", "users", "servers", "channels",
             "presence_history", "user_profile_settings", "web_visitors_daily", "web_pageviews_daily", "web_accounts"]


@admin_bp.route("/admin", methods=["GET"])
@admin_required
def admin_page():
    return render_template("admin.html")


@admin_bp.route("/admin/data", methods=["GET"])
@admin_required
def admin_data():
    lang = "en" if request.cookies.get("lang") == "en" else "fr"
    flush_audience(settle_all=False)  # include the last minute of this worker
    return jsonify(cache.get_or_set(("admin", lang), ADMIN_CACHE_SECONDS, lambda: compute_admin_data(lang)))


# ------------------------------------------------------------------------------
# Helpers
# ------------------------------------------------------------------------------

def _rows(sql: str, params=()) -> list[tuple]:
    try:
        return list(db.execute_sql(sql, params).fetchall())
    except Exception:
        db.rollback()
        return []


def _one(sql: str, params=(), default=0):
    rows = _rows(sql, params)
    return rows[0][0] if rows and rows[0][0] is not None else default


def _days(n: int) -> list[date]:
    today = datetime.now(timezone.utc).date()
    return [today - timedelta(days=n - 1 - i) for i in range(n)]


def _day_label(d: date, lang: str) -> str:
    return f"{d.day} {get_month_abbr(d.month, lang)}"


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

def compute_admin_data(lang: str = "fr") -> dict:
    fr = lang == "fr"
    today = datetime.now(timezone.utc).date()
    d30, d90 = _days(30), _days(90)

    # ---------------- Traffic ----------------
    views = _rows("SELECT day, SUM(views) FROM web_pageviews_daily WHERE day >= %s GROUP BY day", (d90[0],))
    uniques = _rows("SELECT day, COUNT(*) FROM web_visitors_daily WHERE day >= %s GROUP BY day", (d90[0],))
    views_s, uniques_s = _series(views, d90), _series(uniques, d90)

    def period(series, n, offset=0):
        end = len(series) - offset
        return sum(series[max(0, end - n):end])

    pages = _rows("SELECT page_key, SUM(views) FROM web_pageviews_daily WHERE day >= %s GROUP BY page_key ORDER BY 2 DESC", (d30[0],))
    referrers = _rows("SELECT domain, SUM(views) FROM web_referrers_daily WHERE day >= %s GROUP BY domain ORDER BY 2 DESC LIMIT 50", (d30[0],))
    hourly = dict(_rows("SELECT hour, SUM(views) FROM web_hourly_views WHERE day >= %s GROUP BY hour", (d30[0],)))
    devices = _rows("SELECT is_mobile, COUNT(*) FROM web_visitors_daily WHERE day >= %s GROUP BY is_mobile", (d30[0],))
    langs = _rows("SELECT lang, COUNT(*) FROM web_visitors_daily WHERE day >= %s GROUP BY lang", (d30[0],))
    searches = _rows("SELECT term, SUM(hits) FROM web_searches_daily WHERE day >= %s GROUP BY term ORDER BY 2 DESC LIMIT 100", (d30[0],))

    def top_entities(kind):
        # Rows recorded before v3.16.0 may hold a username or an id for the same member: merge them by target
        rows = _rows("SELECT entity_id, SUM(views) FROM web_entity_views_daily WHERE kind = %s AND day >= %s GROUP BY entity_id ORDER BY 2 DESC LIMIT 200", (kind, d30[0]))
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
        "labels": [_day_label(d, lang) for d in d90],
        "views": views_s,
        "uniques": uniques_s,
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
    active_daily = _rows("SELECT day, COUNT(*) FROM web_logins_daily WHERE day >= %s GROUP BY day", (d30[0],))
    active7 = int(_one("SELECT COUNT(DISTINCT user_id) FROM web_logins_daily WHERE day >= %s", (today - timedelta(days=6),)))
    active30 = int(_one("SELECT COUNT(DISTINCT user_id) FROM web_logins_daily WHERE day >= %s", (d30[0],)))
    recent = _rows(
        "SELECT a.user_id, u.username, u.avatar, a.last_login_at, a.login_count, a.first_login_at FROM web_accounts a "
        "LEFT JOIN users u ON u.user_id = a.user_id ORDER BY a.last_login_at DESC LIMIT 100")
    accounts = {
        "total": accounts_total,
        "members_total": members_total,
        "linked_percent": round(accounts_total / members_total * 100, 1) if members_total else 0,
        "new_week": new_week,
        "active7": active7,
        "active30": active30,
        "weeks": {"labels": [_day_label(w, lang) for w, _ in weeks], "values": [int(n) for _, n in weeks]},
        "active_daily": {"labels": [_day_label(d, lang) for d in d30], "values": _series(active_daily, d30)},
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
        changed = (accent not in (None, "sky") or mode == "image" or bg or fav or featured or pinned or hidden or is_private)
        customized += bool(changed)
        private += is_private
        favorite += bool(fav)
        accent_c[accent or "sky"] += 1
        banner_mode_c[mode] += 1
        if mode == "image":
            banner_c[banner] += 1
        if bg:
            bg_c[bg] += 1
        badge_c.update(featured)
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
    joins = dict(_rows("SELECT DATE_TRUNC('month', first_tracked_at)::date, COUNT(*) FROM servers WHERE first_tracked_at >= %s GROUP BY 1", (month_start,)))
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
    sizes = _rows(
        "SELECT c.relname, GREATEST(c.reltuples, 0)::bigint, pg_total_relation_size(c.oid) FROM pg_class c "
        "WHERE c.relname = ANY(%s) AND c.relkind = 'r' ORDER BY 3 DESC", (DB_TABLES,))
    bot = {
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
        "months": {"labels": [f"{get_month_abbr(m.month, lang)} {m.year}" for m in months],
                   "joins": [int(joins.get(m, 0)) for m in months], "leaves": [int(leaves.get(m, 0)) for m in months]},
        "tables": [{"name": n, "rows": int(r), "mb": round(b / 1048576, 1)} for n, r, b in sizes],
        "db_mb": round(int(_one("SELECT pg_database_size(current_database())")) / 1048576, 1),
    }

    # ---------------- Site health ----------------
    status_rows = _rows("SELECT day, status, SUM(hits) FROM web_status_daily WHERE day >= %s GROUP BY day, status", (d30[0],))
    by_status = {s: {} for s in (404, 429, 500)}
    for day, status, hits in status_rows:
        by_status.setdefault(int(status), {})[day] = int(hits)
    top_404 = _rows("SELECT path_key, SUM(hits) FROM web_status_daily WHERE status = 404 AND day >= %s GROUP BY path_key ORDER BY 2 DESC LIMIT 50", (d30[0],))
    from app.routes.graphs import LAST_REFRESH
    health = {
        "labels": [_day_label(d, lang) for d in d30],
        "s404": [by_status[404].get(d, 0) for d in d30],
        "s429": [by_status[429].get(d, 0) for d in d30],
        "s500": [by_status[500].get(d, 0) for d in d30],
        "top_404": [{"name": p, "value": int(n)} for p, n in top_404],
        "analytics_refresh": dict(LAST_REFRESH),
    }

    # ---------------- Bot commands (table written by the bot since bot v3.1.0) ----------------
    cmd_daily = _rows("SELECT created_at::date, COUNT(*) FROM bot_command_events WHERE created_at >= %s GROUP BY 1", (d30[0],))
    cmd_top = _rows(
        "SELECT command, COUNT(*), SUM(CASE WHEN success THEN 0 ELSE 1 END), "
        "ROUND(AVG(duration_ms)), PERCENTILE_CONT(0.95) WITHIN GROUP (ORDER BY duration_ms) "
        "FROM bot_command_events WHERE created_at >= %s GROUP BY command ORDER BY 2 DESC", (d30[0],))
    cmd_servers = _rows(
        "SELECT e.server_id, s.servername, s.avatar, COUNT(*) FROM bot_command_events e LEFT JOIN servers s ON s.server_id = e.server_id "
        "WHERE e.created_at >= %s AND e.server_id IS NOT NULL GROUP BY e.server_id, s.servername, s.avatar ORDER BY 4 DESC LIMIT 50", (d30[0],))
    cmd_options = _rows(
        "SELECT options, COUNT(*) FROM bot_command_events WHERE created_at >= %s AND options <> '' GROUP BY options ORDER BY 2 DESC LIMIT 50", (d30[0],))
    cmd_dm = int(_one("SELECT COUNT(*) FROM bot_command_events WHERE created_at >= %s AND server_id IS NULL", (d30[0],)))
    cmd_total = sum(int(r[1]) for r in cmd_top)
    cmd_failed = sum(int(r[2] or 0) for r in cmd_top)
    dm_label = "refusée en DM" if fr else "refused in DM"
    commands = {
        "total": cmd_total,
        "today": _series(cmd_daily, d30)[-1],
        "failed": cmd_failed,
        "failed_percent": round(cmd_failed / cmd_total * 100, 1) if cmd_total else 0,
        "dm": cmd_dm,
        "labels": [_day_label(d, lang) for d in d30],
        "daily": _series(cmd_daily, d30),
        "top": [{"name": f"/{c}", "value": int(n)} for c, n, _, _, _ in cmd_top],
        "perf": [{"name": f"/{c}", "count": int(n), "failed": int(f or 0), "avg_ms": int(a or 0), "p95_ms": int(p or 0)} for c, n, f, a, p in cmd_top],
        "servers": [{"name": name or str(sid), "avatar": avatar, "url": url_for("server_profile.server", server_id=sid), "value": int(n)}
                    for sid, name, avatar, n in cmd_servers],
        "options": [{"name": o.replace("dm_refused", dm_label), "value": int(n)} for o, n in cmd_options],
    }

    return {
        "commands": commands,
        "overview": {
            "views_today": views_s[-1], "views_7": period(views_s, 7), "views_7_prev": period(views_s, 7, 7),
            "views_30": period(views_s, 30), "views_30_prev": period(views_s, 30, 30),
            "uniques_today": uniques_s[-1], "uniques_7_avg": round(period(uniques_s, 7) / 7, 1),
            "accounts": accounts_total, "accounts_new_week": new_week,
            "customized": customized, "customized_percent": customization["customized_percent"],
            "servers_present": bot["servers_present"], "servers_active30": bot["servers_active30"],
            "delta_7": _delta(period(views_s, 7), period(views_s, 7, 7)),
            "delta_30": _delta(period(views_s, 30), period(views_s, 30, 30)),
            "tracking_since": str(_one("SELECT MIN(day) FROM web_pageviews_daily", default="")) or None,
        },
        "traffic": traffic,
        "accounts": accounts,
        "customization": customization,
        "bot": bot,
        "health": health,
        "generated_at": datetime.utcnow().isoformat(timespec="seconds"),
    }
