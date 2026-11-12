"""Timeline: a leaderboard race built by the visitor (Outils > Timeline).

Running totals of voice hours or messages, month by month, for:
- the best members of all servers or of one server (top 10, 20 or 30 of each month), or
- members picked by hand (up to 20).

Bots and members whose profile is private never appear, whichever way they were chosen.
Measured activity counts in the month it happened. The totals imported from the old bot (one row per member,
dated October 2024) are spread evenly from the member's first day on the server to that date, as on the charts.
"""

import json
import logging
from collections import defaultdict
from datetime import date

from app.cache import cache
from app.database import db
from app.functions import LEGACY_IMPORT_AT, get_bot_user_ids
from app.i18n import month_year

log = logging.getLogger(__name__)

HOURGLASS_BOT_ID = 1210665993328926750
METRICS = ("voice", "messages")
TOPS = (10, 20, 30)
DEFAULT_TOP = 20
MAX_PICKS = 20
POOL = 100  # members whose monthly totals are worked out in top mode (the most active of all time in scope)
CACHE_SECONDS = 600


def _next_month(d: date) -> date:
    return date(d.year + (d.month == 12), d.month % 12 + 1, 1)


def _months_between(start: date, end: date) -> list[date]:
    out, cur = [], start
    while cur <= end:
        out.append(cur)
        cur = _next_month(cur)
    return out


def parse_month(value: str | None) -> date | None:
    """'2025-03' -> date(2025, 3, 1); None when missing or malformed."""
    try:
        year, month = (int(p) for p in str(value or "").split("-")[:2])
        if 2015 <= year <= 2100 and 1 <= month <= 12:
            return date(year, month, 1)
    except (TypeError, ValueError):
        pass
    return None


def private_user_ids() -> frozenset[int]:
    """Members whose profile is private (user_profile_settings.layout {"private": true})."""
    def compute() -> frozenset[int]:
        try:
            rows = db.execute_sql("SELECT user_id, layout FROM user_profile_settings WHERE layout LIKE %s", ("%private%",)).fetchall()
        except Exception:
            db.rollback()
            return frozenset()
        hidden = set()
        for uid, layout in rows:
            try:
                if json.loads(layout or "{}").get("private"):
                    hidden.add(int(uid))
            except (ValueError, AttributeError):
                continue
        return frozenset(hidden)

    return cache.get_or_set(("timeline_private_ids",), 60, compute)


def hidden_user_ids() -> frozenset[int]:
    """Who the Timeline never shows: bots and private profiles."""
    return get_bot_user_ids() | private_user_ids() | {HOURGLASS_BOT_ID}


def timeline_servers() -> list[dict]:
    """Servers offered in the scope list, the most active first."""
    def compute() -> list[dict]:
        rows = db.execute_sql(
            "SELECT s.server_id, sv.servername, sv.avatar FROM stats s JOIN servers sv ON sv.server_id = s.server_id "
            "GROUP BY s.server_id, sv.servername, sv.avatar HAVING COUNT(*) >= 3 ORDER BY SUM(s.seconds) DESC").fetchall()
        return [{"id": str(r[0]), "name": r[1] or f"#{r[0]}", "avatar": r[2]} for r in rows]

    return cache.get_or_set(("timeline_servers",), CACHE_SECONDS, compute)


def server_exists(server_id: int) -> bool:
    return any(s["id"] == str(server_id) for s in timeline_servers())


def search_members(q: str, server_id: int | None, limit: int = 8) -> list[dict]:
    """Members to pick by name, in scope, most active first (bots and private profiles left out)."""
    q = (q or "").strip()[:40]
    if not q:
        return []
    hidden = hidden_user_ids()
    scope = "AND s.server_id = %s " if server_id else ""
    params: list = [f"%{q}%"] + ([int(server_id)] if server_id else []) + [limit + 30]
    rows = db.execute_sql(
        "SELECT u.user_id, u.username, u.avatar FROM users u JOIN stats s ON s.user_id = u.user_id "
        f"WHERE u.username ILIKE %s {scope}GROUP BY u.user_id, u.username, u.avatar "
        "ORDER BY SUM(s.seconds) + SUM(s.messages) * 60 DESC LIMIT %s", params).fetchall()
    out = [{"id": str(r[0]), "name": r[1] or f"#{r[0]}", "avatar": r[2]} for r in rows if int(r[0]) not in hidden]
    return out[:limit]


def _top_pool(metric: str, server_id: int | None, hidden: frozenset[int]) -> list[dict]:
    column = "seconds" if metric == "voice" else "messages"
    scope = "WHERE s.server_id = %s " if server_id else ""
    params = ([int(server_id)] if server_id else []) + [POOL + len(hidden)]
    rows = db.execute_sql(
        f"SELECT s.user_id, u.username, u.avatar FROM stats s LEFT JOIN users u ON u.user_id = s.user_id {scope}"
        f"GROUP BY s.user_id, u.username, u.avatar HAVING SUM(s.{column}) > 0 ORDER BY SUM(s.{column}) DESC LIMIT %s",
        params).fetchall()
    people = [{"id": int(r[0]), "name": r[1] or f"#{r[0]}", "avatar": r[2]} for r in rows if int(r[0]) not in hidden]
    return people[:POOL]


def _picked(ids: list[int], hidden: frozenset[int]) -> tuple[list[dict], list[dict]]:
    """(members to show, in the order given; skipped [{id, reason}]) for hand-picked ids."""
    skipped = [{"id": str(uid), "reason": "hidden"} for uid in ids if uid in hidden]
    wanted = [uid for uid in ids if uid not in hidden]
    found = {}
    if wanted:
        for uid, name, avatar in db.execute_sql(
                "SELECT user_id, username, avatar FROM users WHERE user_id = ANY(%s)", (wanted,)).fetchall():
            found[int(uid)] = {"id": int(uid), "name": name or f"#{uid}", "avatar": avatar}
    skipped += [{"id": str(uid), "reason": "unknown"} for uid in wanted if uid not in found]
    return [found[uid] for uid in wanted if uid in found], skipped


def _monthly(metric: str, server_id: int | None, ids: list[int]) -> dict[date, dict[int, float]]:
    """{month: {user_id: seconds or messages}} with the old bot's totals spread over the months they cover."""
    per_month: dict[date, dict[int, float]] = defaultdict(lambda: defaultdict(float))
    head = (int(server_id),) if server_id else ()
    if metric == "voice":
        scope = "server_id = %s AND " if server_id else ""
        measured = ("SELECT user_id, date_trunc('month', joined_at)::date, SUM(duration_seconds) FROM voice_sessions "
                    f"WHERE {scope}user_id = ANY(%s) AND NOT (joined_at = %s AND left_at = joined_at) GROUP BY 1, 2")
        imported = ("SELECT v.user_id, v.duration_seconds, s.date_creation FROM voice_sessions v LEFT JOIN stats s "
                    "ON s.user_id = v.user_id AND s.server_id = v.server_id WHERE "
                    + ("v.server_id = %s AND " if server_id else "")
                    + "v.user_id = ANY(%s) AND v.joined_at = %s AND v.left_at = v.joined_at AND v.duration_seconds > 0")
    else:
        scope = "server_id = %s AND " if server_id else ""
        measured = ("SELECT user_id, date_trunc('month', created_at)::date, SUM(count) FROM message_events "
                    f"WHERE {scope}user_id = ANY(%s) AND created_at <> %s GROUP BY 1, 2")
        imported = ("SELECT m.user_id, m.count, s.date_creation FROM message_events m LEFT JOIN stats s "
                    "ON s.user_id = m.user_id AND s.server_id = m.server_id WHERE "
                    + ("m.server_id = %s AND " if server_id else "")
                    + "m.user_id = ANY(%s) AND m.created_at = %s AND m.count > 0")

    for uid, month, amount in db.execute_sql(measured, head + (ids, LEGACY_IMPORT_AT)).fetchall():
        per_month[month][int(uid)] += float(amount or 0)

    import_month = LEGACY_IMPORT_AT.date().replace(day=1)
    for uid, amount, since in db.execute_sql(imported, head + (ids, LEGACY_IMPORT_AT)).fetchall():
        first = since.date() if hasattr(since, "date") else (since or import_month)
        span = _months_between(min(first.replace(day=1), import_month), import_month)
        for month in span:
            per_month[month][int(uid)] += float(amount or 0) / len(span)
    return per_month


def build_timeline(metric: str, server_id: int | None, picks: list[int], top: int,
                   start: date | None, end: date | None, lang: str) -> dict:
    """The race asked for, ready for the page (see the module docstring). Cached for 10 minutes."""
    key = ("timeline", metric, server_id, tuple(picks), top, start, end, lang)
    return cache.get_or_set(key, CACHE_SECONDS, lambda: _build(metric, server_id, picks, top, start, end, lang))


def _build(metric, server_id, picks, top, start, end, lang) -> dict:
    hidden = hidden_user_ids()
    skipped: list[dict] = []
    if picks:
        people, skipped = _picked(picks, hidden)
    else:
        people = _top_pool(metric, server_id, hidden)
    result = {"metric": metric, "mode": "picks" if picks else "top", "top": top, "members": [], "frames": [],
              "skipped": skipped, "range": None, "period": None}
    if not people:
        return result

    ids = [p["id"] for p in people]
    per_month = _monthly(metric, server_id, ids)
    this_month = date.today().replace(day=1)
    if not per_month:
        return result
    first = min(per_month)
    result["range"] = {"min": first.strftime("%Y-%m"), "max": this_month.strftime("%Y-%m")}

    lo = max(start or first, first)
    hi = min(end or this_month, this_month)
    if lo > hi:
        lo = hi
    months = _months_between(lo, hi)

    # Running totals from the first month of the period (a race "of 2025" starts everyone at zero in January)
    running = {uid: 0.0 for uid in ids}
    totals = []
    for month in months:
        gains = per_month.get(month, {})
        for uid, amount in gains.items():
            if uid in running:
                running[uid] += amount
        totals.append((month, dict(running), dict(gains)))

    if picks:
        kept = people
    else:
        # Only the members who were in the top N at least once: every month then shows its real top N
        shown = set()
        for _, month_totals, _ in totals:
            shown.update(sorted((u for u in ids if month_totals[u] > 0), key=lambda u: -month_totals[u])[:top])
        kept = [p for p in people if p["id"] in shown]

    scale = 3600 if metric == "voice" else 1
    digits = 1 if metric == "voice" else 0

    def value(v: float):
        return round(v / scale, digits) if digits else int(round(v / scale))

    frames = [{
        "month": month.strftime("%Y-%m"),
        "label": month_year(month.month, month.year, lang),
        "values": [value(month_totals[p["id"]]) for p in kept],
        "gains": [value(gains.get(p["id"], 0)) for p in kept],
        "partial": month == this_month,
        "estimated": month <= LEGACY_IMPORT_AT.date().replace(day=1),
    } for month, month_totals, gains in totals]
    # Top mode: leading months where nobody had anything yet are skipped
    if not picks:
        while len(frames) > 1 and not any(frames[0]["values"]):
            frames.pop(0)

    result.update({
        "members": [{"id": str(p["id"]), "name": p["name"], "avatar": p["avatar"]} for p in kept],
        "frames": frames if kept else [],
        "period": {"from": frames[0]["month"], "to": frames[-1]["month"]} if frames and kept else None,
    })
    return result
