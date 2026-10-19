"""Data visualization and analytics graph routes."""

import json
import logging
import os
import re
import tempfile
import threading
import time
from datetime import datetime, timedelta
from flask import Blueprint, current_app, jsonify, render_template, request
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
    shared_month_totals,
)

graphs_bp = Blueprint("graphs", __name__)

log = logging.getLogger(__name__)

# Global analytics are identical for every visitor sharing a language and timezone. They never make a
# visitor wait once computed:
#   - younger than GRAPHS_CACHE_TTL_SECONDS: served as is;
#   - older (up to GRAPHS_CACHE_MAX_AGE_SECONDS): served immediately while ONE background thread recomputes;
#   - missing or too old: computed once (concurrent visitors of the same key wait for that single run).
# Each result is kept in the worker's memory AND in a JSON file shared by all the Gunicorn workers of the
# container: a worker that just started (or was recycled by --max-requests) or that never saw a timezone
# reuses what another worker computed instead of making its visitor wait. A lock file lets a single worker
# refresh a key at a time. The default key (French, Europe/Paris) is also warmed at startup.
GRAPHS_CACHE_TTL_SECONDS = 300
GRAPHS_CACHE_MAX_AGE_SECONDS = 6 * 3600
REFRESH_LOCK_SECONDS = 120  # a refresh lock older than this is considered abandoned (crashed worker)
DEFAULT_CACHE_KEY = ("fr", "Europe/Paris")
SHARED_CACHE_DIR = os.environ.get("GRAPHS_CACHE_DIR") or os.path.join(tempfile.gettempdir(), "hourglass-graphs")
_graphs_cache: dict[tuple[str, str], tuple[float, dict]] = {}  # key -> (time.time() of the computation, data)
_graphs_cache_lock = threading.Lock()   # guards _graphs_cache, _refreshing and _key_locks
_refreshing: set[tuple[str, str]] = set()
_key_locks: dict[tuple[str, str], threading.Lock] = {}
LAST_REFRESH: dict = {}  # shown on the admin page (last background refresh of this worker)


def _shared_path(key: tuple[str, str], suffix: str = ".json") -> str:
    name = re.sub(r"[^A-Za-z0-9_-]", "_", f"{key[0]}__{key[1]}")
    return os.path.join(SHARED_CACHE_DIR, name + suffix)


def _read_shared(key: tuple[str, str]) -> tuple[float, dict] | None:
    """Result written by any worker, if it is not too old."""
    path = _shared_path(key)
    try:
        ts = os.path.getmtime(path)
        if time.time() - ts >= GRAPHS_CACHE_MAX_AGE_SECONDS:
            return None
        with open(path, encoding="utf-8") as f:
            return ts, json.load(f)
    except (OSError, ValueError):
        return None


def _write_shared(key: tuple[str, str], data: dict) -> None:
    path = _shared_path(key)
    tmp = f"{path}.{os.getpid()}.{threading.get_ident()}.tmp"
    try:
        os.makedirs(SHARED_CACHE_DIR, exist_ok=True)
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, separators=(",", ":"), default=str)
        os.replace(tmp, path)  # atomic: readers never see a half-written file
    except OSError as e:
        log.warning("Could not write the shared analytics cache %s: %s", path, e)
        try:
            os.remove(tmp)
        except OSError:
            pass


def _claim_refresh(key: tuple[str, str]) -> bool:
    """True when this worker may refresh the key (no other worker is doing it right now)."""
    lock = _shared_path(key, ".lock")
    for _ in range(2):
        try:
            os.makedirs(SHARED_CACHE_DIR, exist_ok=True)
            os.close(os.open(lock, os.O_CREAT | os.O_EXCL | os.O_WRONLY))
            return True
        except FileExistsError:
            try:
                if time.time() - os.path.getmtime(lock) < REFRESH_LOCK_SECONDS:
                    return False
                os.remove(lock)  # abandoned by a worker that died mid-refresh: take it over
            except OSError:
                pass
        except OSError:
            return True  # no writable temp dir: behave as before (per-worker refresh)
    return False


def _release_refresh(key: tuple[str, str]) -> None:
    try:
        os.remove(_shared_path(key, ".lock"))
    except OSError:
        pass


def _store(key: tuple[str, str], data: dict, ts: float | None = None, share: bool = True) -> None:
    now = time.time()
    with _graphs_cache_lock:
        _graphs_cache[key] = (ts or now, data)
        for k in [k for k, (t, _) in _graphs_cache.items() if now - t >= GRAPHS_CACHE_MAX_AGE_SECONDS]:
            del _graphs_cache[k]
    if share:
        _write_shared(key, data)


def _compute(lang: str) -> dict:
    with shared_month_totals():  # the per-month totals feed both the bars and the cumulative curves
        return compute_graphs_data(lang=lang)


def _compute_outside_request(app, key: tuple[str, str]) -> dict:
    """Compute in a background thread: own DB connection, and the visitor's language and timezone as cookies."""
    lang, tz_name = key
    with app.test_request_context("/", headers={"Cookie": f"lang={lang}; user_tz={tz_name}"}):
        db.connect(reuse_if_open=True)
        try:
            return _compute(lang)
        finally:
            if not db.is_closed():
                db.close()


def _refresh_in_background(app, key: tuple[str, str], delay: float = 0) -> None:
    def run():
        if delay:
            time.sleep(delay)  # warm-up: let the application finish starting first
        claimed = False
        try:
            # Another worker may already have a fresh result, or be computing one: reuse it
            shared = _read_shared(key)
            if shared and time.time() - shared[0] < GRAPHS_CACHE_TTL_SECONDS:
                _store(key, shared[1], ts=shared[0], share=False)
                return
            claimed = _claim_refresh(key)
            if not claimed:
                if shared:
                    _store(key, shared[1], ts=shared[0], share=False)
                return
            started = time.monotonic()
            _store(key, _compute_outside_request(app, key))
            elapsed_ms = (time.monotonic() - started) * 1000
            LAST_REFRESH.update({"key": list(key), "at": datetime.utcnow().isoformat(timespec="seconds"), "ms": round(elapsed_ms)})
            # Visitors never wait for this, but a slow refresh means the database needs attention
            (log.warning if elapsed_ms > 2000 else log.info)("Analytics cache %s refreshed in %.0f ms", key, elapsed_ms)
        except Exception:
            log.exception("Analytics cache refresh failed for %s", key)
        finally:
            if claimed:
                _release_refresh(key)
            with _graphs_cache_lock:
                _refreshing.discard(key)

    threading.Thread(target=run, name=f"graphs-refresh-{key[0]}", daemon=True).start()


def get_cached_graphs_data(lang: str, tz_name: str, wait: bool = True) -> dict | None:
    """Analytics data for this language/timezone, without waiting whenever a previous result exists.

    With wait=False, returns None instead of computing when no result exists yet (used to inline the
    data in the page only when it is instantly available)."""
    key = (lang, tz_name)
    with _graphs_cache_lock:
        hit = _graphs_cache.get(key)
    if not hit or time.time() - hit[0] >= GRAPHS_CACHE_TTL_SECONDS:
        # Stale or missing here: another worker may have a newer result in the shared file
        shared = _read_shared(key)
        if shared and (not hit or shared[0] > hit[0]):
            _store(key, shared[1], ts=shared[0], share=False)
            hit = shared

    with _graphs_cache_lock:
        if hit:
            age = time.time() - hit[0]
            if age < GRAPHS_CACHE_TTL_SECONDS:
                return hit[1]
            if age < GRAPHS_CACHE_MAX_AGE_SECONDS:
                if key not in _refreshing:
                    _refreshing.add(key)
                    _refresh_in_background(current_app._get_current_object(), key)
                return hit[1]
        if not wait:
            return None
        key_lock = _key_locks.setdefault(key, threading.Lock())

    # Nothing usable yet: a single computation per key, the other visitors wait for its result
    with key_lock:
        with _graphs_cache_lock:
            hit = _graphs_cache.get(key)
            if hit and time.time() - hit[0] < GRAPHS_CACHE_TTL_SECONDS:
                return hit[1]
        data = _compute(lang)
        _store(key, data)
        return data


def warm_graphs_cache(app) -> None:
    """Compute the default analytics once the worker has started, so the first visitor never waits."""
    if os.environ.get("GRAPHS_WARMUP", "true").lower() in ("0", "false", "no"):
        return
    with _graphs_cache_lock:
        if DEFAULT_CACHE_KEY in _refreshing:
            return
        _refreshing.add(DEFAULT_CACHE_KEY)
    _refresh_in_background(app, DEFAULT_CACHE_KEY, delay=2)

graphs_bp.record_once(lambda state: warm_graphs_cache(state.app))


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


def _visitor_lang() -> str:
    lang = request.cookies.get("lang", "fr")
    return lang if lang in ("fr", "en") else "fr"


@graphs_bp.route("/graphs", methods=["GET"])
def graphs():
    """Analytics page. When the data is already cached it is inlined in the page (no second request);
    otherwise the page renders immediately and the charts load from /api/graphs/data."""
    return render_template("graphs.html", initial_data=get_cached_graphs_data(_visitor_lang(), get_user_timezone(), wait=False))


@graphs_bp.route("/api/graphs/data", methods=["GET"])
def api_graphs_data():
    """Asynchronous JSON endpoint returning analytical metrics for background loading."""
    return jsonify(get_cached_graphs_data(_visitor_lang(), get_user_timezone()))
