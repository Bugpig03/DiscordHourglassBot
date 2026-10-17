"""Data visualization and analytics graph routes."""

import threading
import time
from datetime import datetime, timedelta
from flask import Blueprint, render_template, request, jsonify
from peewee import fn, JOIN
from app.database import db, Stats, Servers
from app.functions import (
    get_first_of_month_hours_sum,
    get_first_of_month_messages_sum,
    get_daily_hours_progression,
    get_daily_messages_progression,
    get_monthly_hours_diff,
    get_monthly_messages_diff,
    get_daily_activity_last_30_days,
    get_top_10_users_by_hours,
    get_top_10_users_by_messages,
    get_hourly_activity_distribution,
    get_presence_history_48h,
    get_monthly_new_users_growth,
    get_month_abbr,
    get_partial_period,
    get_hourly_punchcard_data,
    get_user_timezone,
)

graphs_bp = Blueprint("graphs", __name__)

# Global analytics are identical for every visitor sharing a language and timezone:
# cache them per Gunicorn worker for 5 minutes instead of running ~30 SQL queries per page view.
GRAPHS_CACHE_TTL_SECONDS = 300
_graphs_cache: dict[tuple[str, str], tuple[float, dict]] = {}
_graphs_cache_lock = threading.Lock()


def get_cached_graphs_data(lang: str, tz_name: str) -> dict:
    """Return graph data from the in-memory cache, recomputing it once expired."""
    key = (lang, tz_name)
    now = time.monotonic()
    with _graphs_cache_lock:
        cached = _graphs_cache.get(key)
        if cached and now - cached[0] < GRAPHS_CACHE_TTL_SECONDS:
            return cached[1]
        # Computing under the lock avoids several threads recomputing the same expired entry at once
        data = compute_graphs_data(lang=lang)
        for k in [k for k, (ts, _) in _graphs_cache.items() if now - ts >= GRAPHS_CACHE_TTL_SECONDS]:
            del _graphs_cache[k]
        _graphs_cache[key] = (now, data)
        return data


def _day_label(date_str: str, lang: str) -> str:
    d = datetime.strptime(date_str, "%Y-%m-%d")
    return f"{d.day} {get_month_abbr(d.month, lang)}"


def _month_label(date_str: str, lang: str) -> str:
    d = datetime.strptime(date_str, "%Y-%m-%d")
    if d.day != 1:  # first/last point of a cumulative series (bot start date, today)
        return f"{d.day} {get_month_abbr(d.month, lang)} {d.year}"
    return f"{get_month_abbr(d.month, lang)} {d.year}"


def _aligned(rows_a: list[dict], key_a: str, rows_b: list[dict], key_b: str, date_key: str, carry: bool) -> tuple[list, list, list]:
    """Merge two series on their date: missing points are 0 (per period) or the previous value (cumulative)."""
    a = {r[date_key]: r[key_a] for r in rows_a}
    b = {r[date_key]: r[key_b] for r in rows_b}
    dates = sorted(set(a) | set(b))
    out_a, out_b, last_a, last_b = [], [], 0, 0
    for d in dates:
        last_a = a.get(d, last_a if carry else 0)
        last_b = b.get(d, last_b if carry else 0)
        out_a.append(last_a)
        out_b.append(last_b)
    return dates, out_a, out_b


def _window_activity(since: datetime, until: datetime | None = None) -> dict:
    """Voice hours, messages, active members and active servers between two UTC dates."""
    params = [since] if until is None else [since, until]
    v_range = "joined_at >= %s" + ("" if until is None else " AND joined_at < %s")
    m_range = "created_at >= %s" + ("" if until is None else " AND created_at < %s")
    seconds = db.execute_sql(f"SELECT COALESCE(SUM(duration_seconds), 0) FROM voice_sessions WHERE {v_range}", params).fetchone()[0]
    messages = db.execute_sql(f"SELECT COALESCE(SUM(count), 0) FROM message_events WHERE {m_range}", params).fetchone()[0]
    members, servers = db.execute_sql(
        "SELECT COUNT(DISTINCT user_id), COUNT(DISTINCT server_id) FROM ("
        f" SELECT user_id, server_id FROM voice_sessions WHERE {v_range}"
        f" UNION SELECT user_id, server_id FROM message_events WHERE {m_range}"
        ") t",
        params + params,
    ).fetchone()
    return {
        "hours": round(int(seconds or 0) / 3600, 1),
        "messages": int(messages or 0),
        "members": int(members or 0),
        "servers": int(servers or 0),
    }


def _top_servers(field, lang: str) -> list[dict]:
    rows = (
        Stats.select(Stats.server_id, Servers.servername, Servers.avatar, fn.SUM(field).alias("value"))
        .join(Servers, JOIN.LEFT_OUTER, on=(Stats.server_id == Servers.server_id))
        .group_by(Stats.server_id, Servers.servername, Servers.avatar)
        .order_by(fn.SUM(field).desc())
        .limit(10)
        .dicts()
    )
    default = "Server" if lang == "en" else "Serveur"
    is_voice = field is Stats.seconds
    return [
        {
            "id": str(r["server_id"]),
            "name": r["servername"] or f"{default} {r['server_id']}",
            "avatar": r["avatar"],
            "value": round((r["value"] or 0) / 3600, 1) if is_voice else int(r["value"] or 0),
        }
        for r in rows
    ]


def compute_graphs_data(lang: str = "fr") -> dict:
    """All analytics of the page, grouped by tab (Tendances, Rythme, Communauté)."""
    # Summary cards: last 30 days compared with the 30 days before
    now = datetime.utcnow()
    current = _window_activity(now - timedelta(days=30))
    previous = _window_activity(now - timedelta(days=60), now - timedelta(days=30))

    # Tendances: one chart, voice or messages, per period or cumulative
    daily = get_daily_activity_last_30_days()
    d_dates, d_hours_cumul, d_msgs_cumul = _aligned(
        get_daily_hours_progression(days=30), "total_hours",
        get_daily_messages_progression(days=30), "total_messages", "date", carry=True,
    )
    m_dates, m_hours, m_msgs = _aligned(
        get_monthly_hours_diff(), "hours_this_month",
        get_monthly_messages_diff(), "messages_this_month", "month", carry=False,
    )
    c_dates, c_hours, c_msgs = _aligned(
        get_first_of_month_hours_sum(), "total_hours",
        get_first_of_month_messages_sum(), "total_messages", "month", carry=True,
    )
    trends = {
        "day": {
            "labels": [_day_label(r["date"], lang) for r in daily],
            "hours": [r["hours"] for r in daily],
            "messages": [r["messages"] for r in daily],
            "partial": get_partial_period(daily, "day"),
        },
        "day_cumul": {"labels": [_day_label(d, lang) for d in d_dates], "hours": d_hours_cumul, "messages": d_msgs_cumul},
        "month": {
            "labels": [_month_label(d, lang) for d in m_dates],
            "hours": m_hours,
            "messages": m_msgs,
            "partial": get_partial_period([{"month": d} for d in m_dates], "month"),
        },
        "month_cumul": {"labels": [_month_label(d, lang) for d in c_dates], "hours": c_hours, "messages": c_msgs},
    }

    growth = get_monthly_new_users_growth()
    top_hours = get_top_10_users_by_hours()
    top_msgs = get_top_10_users_by_messages()

    return {
        "summary": {"current": current, "previous": previous},
        "trends": trends,
        "hourly": get_hourly_activity_distribution(server_id=None, user_id=None, lang=lang),
        "punchcard": get_hourly_punchcard_data(),
        # Presence over 48 h and 7 days (the bot keeps 7 days of 15-minute snapshots)
        "presence": {"48h": get_presence_history_48h(lang=lang), "7d": get_presence_history_48h(lang=lang, hours=24 * 7)},
        "growth": {
            "labels": [_month_label(r["month"], lang) for r in growth],
            "new_users": [r["new_users"] for r in growth],
        },
        "top_servers": {"hours": _top_servers(Stats.seconds, lang), "messages": _top_servers(Stats.messages, lang)},
        "top_members": {
            "hours": [{"id": str(r["user_id"]), "name": r["username"], "value": r["hours"]} for r in top_hours],
            "messages": [{"id": str(r["user_id"]), "name": r["username"], "value": r["messages"]} for r in top_msgs],
        },
    }


@graphs_bp.route("/graphs", methods=["GET"])
def graphs():
    """Render the analytics shell immediately; the charts load from /api/graphs/data."""
    return render_template("graphs.html")


@graphs_bp.route("/api/graphs/data", methods=["GET"])
def api_graphs_data():
    """Asynchronous JSON endpoint returning analytical metrics for background loading."""
    lang = request.cookies.get("lang", "fr")
    if lang not in ("fr", "en"):
        lang = "fr"
    data = get_cached_graphs_data(lang, get_user_timezone())
    return jsonify(data)
