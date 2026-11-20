"""Figures of an automatic report (server management > Reports): one server, one period, in the server's time zone.

  - daily: one day; weekly: 7 days; monthly: a calendar month. The previous period of the same length is compared.
  - voice: time spent in voice during the period (sessions cut at its edges), messages: messages sent during it;
  - active members: members with voice time or messages; new members: first activity on the server in the period;
  - top 5 by voice time (messages break ties), without bots or private profiles;
  - activity per hour (daily) or per day (weekly, monthly), and the busiest hour.
Imported totals of the old bot (before October 2024) never fall in a recent period and are left out anyway.
A session still open counts up to the bot's last heartbeat on it (a session the bot failed to close does not grow forever).
"""

import re
from datetime import date, datetime, time, timedelta, timezone
from zoneinfo import ZoneInfo

from app.database import db
from app.functions import LEGACY_IMPORT_AT

KINDS = ("daily", "weekly", "monthly")


def period_bounds(kind: str, start: date) -> tuple[date, date]:
    """[start, end) of the period, as local days."""
    if kind == "daily":
        return start, start + timedelta(days=1)
    if kind == "weekly":
        return start, start + timedelta(days=7)
    first = start.replace(day=1)
    nxt = date(first.year + (first.month == 12), first.month % 12 + 1, 1)
    return first, nxt


def previous_start(kind: str, start: date) -> date:
    if kind == "daily":
        return start - timedelta(days=1)
    if kind == "weekly":
        return start - timedelta(days=7)
    first = start.replace(day=1)
    return date(first.year - (first.month == 1), (first.month - 2) % 12 + 1, 1)


def _utc(day: date, tz: ZoneInfo) -> datetime:
    """Local midnight of a day, as the naive UTC datetimes the database stores."""
    return datetime.combine(day, time(0, 0), tz).astimezone(timezone.utc).replace(tzinfo=None)


def _rows(sql: str, params) -> list[tuple]:
    try:
        return db.execute_sql(sql, params).fetchall()
    except Exception:
        db.rollback()
        return []


def _totals(server_id: int, start: datetime, end: datetime, bots: list[int]) -> dict:
    """Voice seconds, messages and active members of a server between two UTC moments (bots left out)."""
    voice = _rows(
        "SELECT user_id, SUM(GREATEST(0, EXTRACT(EPOCH FROM (LEAST(COALESCE(left_at, GREATEST(last_heartbeat, joined_at), NOW()::timestamp), %s) - GREATEST(joined_at, %s))))) "
        "FROM voice_sessions WHERE server_id = %s AND joined_at < %s AND COALESCE(left_at, GREATEST(last_heartbeat, joined_at), NOW()::timestamp) > %s "
        "AND NOT COALESCE(is_legacy, FALSE) AND NOT (user_id = ANY(%s)) GROUP BY user_id",
        (end, start, server_id, end, start, bots))
    messages = _rows(
        "SELECT user_id, SUM(count) FROM message_events WHERE server_id = %s AND created_at >= %s AND created_at < %s "
        "AND created_at <> %s AND NOT (user_id = ANY(%s)) GROUP BY user_id",
        (server_id, start, end, LEGACY_IMPORT_AT, bots))
    per_user: dict[int, list[float]] = {}
    for uid, sec in voice:
        per_user.setdefault(int(uid), [0.0, 0])[0] += float(sec or 0)
    for uid, n in messages:
        per_user.setdefault(int(uid), [0.0, 0])[1] += int(n or 0)
    active = {uid for uid, (sec, n) in per_user.items() if sec >= 60 or n > 0}
    return {
        "seconds": sum(v[0] for v in per_user.values()),
        "messages": sum(v[1] for v in per_user.values()),
        "active": len(active),
        "per_user": per_user,
    }


def _hour_slots(first: date, last: date, tz: ZoneInfo) -> list[tuple[datetime, datetime, datetime]]:
    """Every local hour of [first, last): (local start, UTC start, UTC end), daylight saving changes included."""
    slots = []
    cursor = datetime.combine(first, time(0, 0), tz).astimezone(timezone.utc)
    stop = datetime.combine(last, time(0, 0), tz).astimezone(timezone.utc)
    while cursor < stop:
        nxt = cursor + timedelta(hours=1)
        slots.append((cursor.astimezone(tz), cursor.replace(tzinfo=None), nxt.replace(tzinfo=None)))
        cursor = nxt
    return slots


def _bucketed(server_id: int, slots: list, bots: list[int]) -> tuple[list[float], list[int]]:
    """Voice seconds spent and messages sent in each slot (UTC start, end), in one query each."""
    starts = [s[1] for s in slots]
    ends = [s[2] for s in slots]
    voice = [0.0] * len(slots)
    messages = [0] * len(slots)
    if not slots:
        return voice, messages
    for idx, sec in _rows(
            "SELECT b.idx, SUM(GREATEST(0, EXTRACT(EPOCH FROM (LEAST(COALESCE(v.left_at, GREATEST(v.last_heartbeat, v.joined_at), NOW()::timestamp), b.be) - GREATEST(v.joined_at, b.bs))))) "
            "FROM unnest(%s::timestamp[], %s::timestamp[]) WITH ORDINALITY AS b(bs, be, idx) "
            "JOIN voice_sessions v ON v.server_id = %s AND v.joined_at < b.be AND COALESCE(v.left_at, GREATEST(v.last_heartbeat, v.joined_at), NOW()::timestamp) > b.bs "
            "AND NOT COALESCE(v.is_legacy, FALSE) AND NOT (v.user_id = ANY(%s)) GROUP BY b.idx",
            (starts, ends, server_id, bots)):
        voice[int(idx) - 1] = float(sec or 0)
    for idx, n in _rows(
            "SELECT b.idx, SUM(m.count) FROM unnest(%s::timestamp[], %s::timestamp[]) WITH ORDINALITY AS b(bs, be, idx) "
            "JOIN message_events m ON m.server_id = %s AND m.created_at >= b.bs AND m.created_at < b.be AND m.created_at <> %s "
            "AND NOT (m.user_id = ANY(%s)) GROUP BY b.idx",
            (starts, ends, server_id, LEGACY_IMPORT_AT, bots)):
        messages[int(idx) - 1] = int(n or 0)
    return voice, messages


def _delta(cur: float, prev: float) -> float | None:
    return round((cur - prev) / prev * 100) if prev else None


def compute_report(server_id: int, kind: str, start: date, tz_name: str) -> dict:
    """Everything the report card shows (see the module docstring)."""
    from app.functions import get_bot_user_ids
    from app.timeline import hidden_user_ids

    if not re.fullmatch(r"[A-Za-z0-9_+\-/]+", tz_name or ""):  # the zone name goes into the SQL text
        tz_name = "Europe/Paris"
    tz = ZoneInfo(tz_name)
    first, last = period_bounds(kind, start)
    p_first, p_last = period_bounds(kind, previous_start(kind, first))
    s_utc, e_utc = _utc(first, tz), _utc(last, tz)
    bots = [int(b) for b in get_bot_user_ids()] or [0]

    cur = _totals(server_id, s_utc, e_utc, bots)
    prev = _totals(server_id, _utc(p_first, tz), _utc(p_last, tz), bots)

    new_members = int((_rows(
        "SELECT COUNT(*) FROM stats WHERE server_id = %s AND date_creation >= %s AND date_creation < %s AND NOT (user_id = ANY(%s))",
        (server_id, s_utc, e_utc, bots)) or [(0,)])[0][0] or 0)

    # Top 5 by voice time, messages breaking ties; private profiles stay out of a public channel
    hidden = hidden_user_ids()
    ranked = sorted(((uid, v) for uid, v in cur["per_user"].items() if uid not in hidden and (v[0] >= 60 or v[1] > 0)),
                    key=lambda item: (-item[1][0], -item[1][1]))[:5]
    names = {}
    if ranked:
        for uid, name, avatar in _rows("SELECT user_id, username, avatar FROM users WHERE user_id = ANY(%s)", ([u for u, _ in ranked],)):
            names[int(uid)] = (name, avatar)
    top = [{"id": uid, "name": (names.get(uid) or (None, None))[0] or f"#{uid}", "avatar": (names.get(uid) or (None, None))[1],
            "seconds": v[0], "messages": v[1]} for uid, v in ranked]

    # Activity over the period, split exactly: each local hour (daily) or day gets the voice time spent in it
    hourly = _hour_slots(first, last, tz)
    voice_h, msg_h = _bucketed(server_id, hourly, bots)
    if kind == "daily":
        keys = list(range(24))
        voice_by, msg_by = {k: 0.0 for k in keys}, {k: 0 for k in keys}
        for (local, _, _), v, m in zip(hourly, voice_h, msg_h):
            voice_by[local.hour] += v
            msg_by[local.hour] += m
    else:
        keys = [first + timedelta(days=i) for i in range((last - first).days)]
        voice_by, msg_by = {k: 0.0 for k in keys}, {k: 0 for k in keys}
        for (local, _, _), v, m in zip(hourly, voice_h, msg_h):
            voice_by[local.date()] += v
            msg_by[local.date()] += m

    # Busiest hour of the day over the period (voice minutes + messages)
    hour_score: dict[int, float] = {}
    for (local, _, _), v, m in zip(hourly, voice_h, msg_h):
        hour_score[local.hour] = hour_score.get(local.hour, 0) + v / 60 + m
    peak = max(hour_score, key=hour_score.get) if hour_score and max(hour_score.values()) > 0 else None

    return {
        "kind": kind, "first": first, "last": last - timedelta(days=1), "timezone": tz_name,
        "seconds": cur["seconds"], "messages": cur["messages"], "active": cur["active"], "new_members": new_members,
        "delta_seconds": _delta(cur["seconds"], prev["seconds"]), "delta_messages": _delta(cur["messages"], prev["messages"]),
        "delta_active": _delta(cur["active"], prev["active"]),
        "top": top,
        "series": [{"key": k, "hours": voice_by[k] / 3600, "messages": msg_by[k]} for k in keys],
        "peak_hour": peak,
    }


def server_timezone(server_id: int) -> str:
    rows = _rows("SELECT timezone FROM server_settings WHERE server_id = %s", (int(server_id),))
    name = rows[0][0] if rows and rows[0][0] else "Europe/Paris"
    try:
        ZoneInfo(name)
        return name
    except Exception:
        return "Europe/Paris"


def last_period_start(kind: str, tz_name: str, today: date | None = None) -> date:
    """First day of the last finished period (preview on the website)."""
    today = today or datetime.now(ZoneInfo(tz_name)).date()
    if kind == "daily":
        return today - timedelta(days=1)
    if kind == "weekly":
        return today - timedelta(days=7)
    first = today.replace(day=1)
    return date(first.year - (first.month == 1), (first.month - 2) % 12 + 1, 1)
