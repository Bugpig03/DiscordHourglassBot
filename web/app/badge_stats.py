"""Every member's badge tiers and the day each tier was reached, for the badge pages (/badge/<id>).

The profile computes a member's badges live; listing all the holders of a badge needs them for everyone, so one
worker recomputes them every hour (under a database lock) into two website tables, no bot table is touched:
  - user_badge_values: per member and badge, the tier, the measured value (value, value2) and the progress
    toward the next tier;
  - user_badge_tiers: per member, badge and reached tier, the day it was reached. before_tracking is set when
    the tier was already reached on 5 Oct 2024: the old bot only kept totals, so the real day is unknown.

Tiers come from gamification.badge_values / _family_badge, the profile's own code, fed with figures read for
everyone at once. Days are rebuilt from the history (voice sessions and message events per day, daily rank
snapshots, top.gg votes); a tier the history cannot date keeps the day it was first seen here.
"""

import logging
import threading
import time
from collections import defaultdict, deque
from datetime import date, datetime, timedelta, timezone

from peewee import DatabaseError

from app.database import create_tables, db
from app.functions import LEGACY_IMPORT_AT, get_bot_user_ids
from app.gamification import BADGE_DEFS, _family_badge, badge_values, xp_for_level, XP_PER_VOTE

log = logging.getLogger(__name__)

REFRESH_SECONDS = 3600
FIRST_RUN_DELAY_SECONDS = 90  # after the best records (45 s), whose rank and 30-day records it reads
LOCK_ID = 727302  # pg advisory lock of the refresh (best_records uses 727301)
IMPORT_DAY = LEGACY_IMPORT_AT.date()
# Daily rank snapshots (historical_stats) start on the day of the import: a tier held on that day may be older
RANK_HISTORY_START = IMPORT_DAY

TABLES = (
    "CREATE TABLE IF NOT EXISTS user_badge_values (user_id BIGINT NOT NULL, badge VARCHAR(16) NOT NULL, "
    "tier SMALLINT NOT NULL, value DOUBLE PRECISION, value2 DOUBLE PRECISION, progress REAL NOT NULL DEFAULT 0, "
    "updated_at TIMESTAMP WITHOUT TIME ZONE NOT NULL, PRIMARY KEY (user_id, badge))",
    "CREATE INDEX IF NOT EXISTS user_badge_values_badge_tier ON user_badge_values (badge, tier)",
    "CREATE TABLE IF NOT EXISTS user_badge_tiers (user_id BIGINT NOT NULL, badge VARCHAR(16) NOT NULL, "
    "tier SMALLINT NOT NULL, reached_on DATE NOT NULL, before_tracking BOOLEAN NOT NULL DEFAULT FALSE, "
    "PRIMARY KEY (user_id, badge, tier))",
    "CREATE INDEX IF NOT EXISTS user_badge_tiers_badge_reached ON user_badge_tiers (badge, reached_on DESC)",
)

DEFS = {d[0]: d for d in BADGE_DEFS}
THRESHOLDS = {d[0]: d[7] for d in BADGE_DEFS}

_enabled = True
_thread_started = False
_retry_at = 0.0  # when a worker that could not create the tables tries again
RETRY_SECONDS = 60


def ensure_tables() -> None:
    global _enabled, _retry_at
    error = create_tables(TABLES)
    _enabled = error is None
    if error is not None:
        _retry_at = time.monotonic() + RETRY_SECONDS
        log.warning("Badge pages unavailable for now (tables could not be created, retried in %d s): %s", RETRY_SECONDS, error)


def enabled() -> bool:
    """True once the tables exist; a worker that lost the startup race tries again (at most once a minute)."""
    if not _enabled and time.monotonic() >= _retry_at:
        ensure_tables()
    return _enabled


# ------------------------------------------------------------------------------
# Figures of every member, read at once (same sources as the profile)
# ------------------------------------------------------------------------------
def _rows(sql: str, params: tuple = ()) -> list:
    return db.execute_sql(sql, params).fetchall()


def _optional_rows(sql: str, params: tuple = ()) -> list:
    """Rows of a table that may not exist yet (topgg_votes, user_best_records): none then."""
    try:
        with db.atomic():
            return _rows(sql, params)
    except DatabaseError:
        return []


def _inputs(now: datetime) -> dict:
    bots = get_bot_user_ids()
    # Totals, servers (those known to the servers table, as on the profile) and first activity
    totals = {uid: (int(sec or 0), int(msgs or 0), int(servers or 0), first)
              for uid, sec, msgs, servers, first in _rows(
                  "SELECT s.user_id, SUM(s.seconds), SUM(s.messages), COUNT(sv.server_id), MIN(s.date_creation) "
                  "FROM stats s LEFT JOIN servers sv ON sv.server_id = s.server_id GROUP BY s.user_id")}
    live = dict(_rows("SELECT user_id, COALESCE(SUM(GREATEST(0, EXTRACT(EPOCH FROM (NOW() - joined_at))::INT)), 0) "
                      "FROM voice_sessions WHERE left_at IS NULL GROUP BY user_id"))
    last30 = dict(_rows("SELECT user_id, COALESCE(SUM(duration_seconds), 0) FROM voice_sessions WHERE joined_at >= %s "
                        "GROUP BY user_id", (now - timedelta(days=30),)))
    # Global voice rank among real members (bots and apps left out), as get_global_rank_by_user_id_seconds
    ranked = sorted(((uid, t[0]) for uid, t in totals.items() if uid not in bots and t[0] > 0), key=lambda r: -r[1])
    ranks, previous, position = {}, None, 0
    for i, (uid, seconds) in enumerate(ranked, start=1):
        if seconds != previous:
            position, previous = i, seconds
        ranks[uid] = position
    records = {uid: {"best_rank": r, "best_rank_on": on, "best_rank_hours": float(h or 0), "best_30d_hours": (s or 0) / 3600.0,
                     "best_30d_end": end, "best_30d_start": end - timedelta(days=29) if isinstance(end, date) else None}
               for uid, r, on, h, s, end in _optional_rows(
                   "SELECT user_id, best_rank, best_rank_on, best_rank_hours, best_30d_seconds, best_30d_end FROM user_best_records")}
    votes = defaultdict(list)
    for uid, created in _optional_rows("SELECT user_id, created_at FROM topgg_votes ORDER BY created_at"):
        votes[int(uid)].append(created)
    return {"bots": bots, "totals": totals, "live": live, "last30": last30, "ranks": ranks, "records": records, "votes": votes}


def _daily(sql: str) -> dict:
    """{user: [(day, amount, includes_import), ...]} sorted by day."""
    out = defaultdict(list)
    for uid, day, amount, imported in _rows(sql):
        out[int(uid)].append((day, float(amount or 0), bool(imported)))
    for series in out.values():
        series.sort(key=lambda r: r[0])
    return out


def _history() -> dict:
    voice = _daily("SELECT user_id, joined_at::date, SUM(duration_seconds), "
                   f"BOOL_OR(joined_at = '{LEGACY_IMPORT_AT.isoformat(sep=' ')}' AND left_at = joined_at) "
                   "FROM voice_sessions WHERE duration_seconds > 0 GROUP BY 1, 2")
    messages = _daily("SELECT user_id, created_at::date, SUM(count), "
                      f"BOOL_OR(created_at = '{LEGACY_IMPORT_AT.isoformat(sep=' ')}') "
                      "FROM message_events WHERE count > 0 GROUP BY 1, 2")
    # Best 30 days: same daily figures as best_records (imported totals left out, a day counts 24 h at most)
    activity = _daily("SELECT user_id, joined_at::date, LEAST(SUM(duration_seconds), 86400), FALSE FROM voice_sessions "
                      "WHERE duration_seconds > 0 AND NOT (left_at = joined_at AND duration_seconds > 86400) GROUP BY 1, 2")
    # Active days, as get_user_best_streak (live sessions count on every day they cover)
    active = defaultdict(set)
    for uid, day in _rows("""
        SELECT v.user_id, gs::date FROM voice_sessions v
        CROSS JOIN LATERAL generate_series(date_trunc('day', v.joined_at),
            date_trunc('day', COALESCE(v.left_at, NOW() AT TIME ZONE 'UTC')), INTERVAL '1 day') AS gs
        WHERE NOT v.is_legacy
        UNION
        SELECT user_id, joined_at::date FROM voice_sessions WHERE is_legacy AND left_at - joined_at <= INTERVAL '36 hours'
        UNION
        SELECT user_id, created_at::date FROM message_events WHERE count > 0"""):
        active[int(uid)].add(day)
    servers = defaultdict(list)
    for uid, first in _rows("SELECT s.user_id, s.date_creation FROM stats s JOIN servers sv ON sv.server_id = s.server_id "
                            "WHERE s.date_creation IS NOT NULL"):
        servers[int(uid)].append(first.date() if isinstance(first, datetime) else first)
    # First day at or above each ranking threshold, from the daily snapshots (last of each day, bots left out)
    humans = "AND user_id NOT IN (SELECT user_id FROM users WHERE is_bot)" if get_bot_user_ids() else ""
    places = THRESHOLDS["rank"]
    filters = ", ".join(f"MIN(day) FILTER (WHERE r <= {p})" for p in places)
    rank_days = {int(r[0]): list(r[1:]) for r in _rows(f"""
        WITH snap AS (
            SELECT DISTINCT ON (created_at::date, user_id, server_id) created_at::date AS day, user_id, seconds
            FROM historical_stats WHERE user_id IS NOT NULL {humans}
            ORDER BY created_at::date, user_id, server_id, created_at DESC
        ), totals AS (
            SELECT day, user_id, SUM(seconds) AS s FROM snap GROUP BY day, user_id HAVING SUM(seconds) > 0
        ), ranked AS (
            SELECT day, user_id, RANK() OVER (PARTITION BY day ORDER BY s DESC) AS r FROM totals
        )
        SELECT user_id, {filters} FROM ranked GROUP BY user_id""")}
    return {"voice": voice, "messages": messages, "activity": activity, "active": active, "servers": servers, "rank": rank_days}


# ------------------------------------------------------------------------------
# Day each tier was reached
# ------------------------------------------------------------------------------
def _crossings(series: list, thresholds: list, scale: float = 1.0) -> list:
    """(day, before_tracking) when the running total first reached each threshold, None when it never did."""
    out, total, i = [None] * len(thresholds), 0.0, 0
    for day, amount, imported in series:
        total += amount / scale
        while i < len(thresholds) and total >= thresholds[i]:
            out[i] = (day, imported)
            i += 1
        if i == len(thresholds):
            break
    return out


def _level_days(voice: list, messages: list, votes: list) -> list:
    """Day the XP (1 per voice minute, 1 per message, 100 per vote) first reached each level threshold."""
    events = defaultdict(lambda: [0.0, 0.0, 0, False])
    for day, seconds, imported in voice:
        events[day][0] += seconds
        events[day][3] |= imported
    for day, count, imported in messages:
        events[day][1] += count
        events[day][3] |= imported
    for created in votes:
        events[created.date()][2] += 1
    needed = [xp_for_level(level) for level in THRESHOLDS["level"]]
    out, seconds, msgs, n_votes, i = [None] * len(needed), 0.0, 0.0, 0, 0
    for day in sorted(events):
        s, m, v, imported = events[day]
        seconds, msgs, n_votes = seconds + s, msgs + m, n_votes + v
        xp = int(seconds) // 60 + int(msgs) + n_votes * XP_PER_VOTE
        while i < len(needed) and xp >= needed[i]:
            out[i] = (day, imported)
            i += 1
    return out


def _window_days(series: list, thresholds: list) -> list:
    """Last day of the first 30-day window whose voice total reached each threshold (hours)."""
    out, window, total, i = [None] * len(thresholds), deque(), 0.0, 0
    for day, seconds, _imported in series:
        window.append((day, seconds))
        total += seconds
        while window and (day - window[0][0]).days > 29:
            total -= window.popleft()[1]
        while i < len(thresholds) and total / 3600.0 >= thresholds[i]:
            out[i] = (day, False)
            i += 1
    return out


def _streak_days(days: set, thresholds: list) -> list:
    """Day a run of consecutive active days first reached each length."""
    out, run, previous, i = [None] * len(thresholds), 0, None, 0
    for day in sorted(days):
        run = run + 1 if previous and (day - previous).days == 1 else 1
        previous = day
        while i < len(thresholds) and run >= thresholds[i]:
            out[i] = (day, False)
            i += 1
    return out


def _tier_days(badge: str, uid: int, data: dict, hist: dict, first_activity) -> list:
    t = THRESHOLDS[badge]
    if badge == "voice":
        return _crossings(hist["voice"].get(uid, []), t, 3600.0)
    if badge == "messages":
        return _crossings(hist["messages"].get(uid, []), t)
    if badge == "level":
        return _level_days(hist["voice"].get(uid, []), hist["messages"].get(uid, []), data["votes"].get(uid, []))
    if badge == "hybrid":
        hours = _crossings(hist["voice"].get(uid, []), [h for h, _m in t], 3600.0)
        msgs = _crossings(hist["messages"].get(uid, []), [m for _h, m in t])
        return [max(a, b, key=lambda x: x[0]) if a and b else None for a, b in zip(hours, msgs)]
    if badge == "activity":
        return _window_days(hist["activity"].get(uid, []), t)
    if badge == "streak":
        return _streak_days(hist["active"].get(uid, set()), t)
    if badge == "servers":
        firsts = sorted(hist["servers"].get(uid, []))
        return [(firsts[n - 1], False) if len(firsts) >= n else None for n in t]
    if badge == "loyalty":
        start = first_activity.date() if isinstance(first_activity, datetime) else first_activity
        today = datetime.now(timezone.utc).date()
        return [(start + timedelta(days=n), False) if start and start + timedelta(days=n) <= today else None for n in t]
    if badge == "rank":
        days = hist["rank"].get(uid) or [None] * len(t)
        out = [(d, d == RANK_HISTORY_START) if d else None for d in days]
        # Reached after the last snapshot (or never snapshotted): the day of the best rank record
        record = data["records"].get(uid) or {}
        for i, place in enumerate(t):
            if out[i] is None and record.get("best_rank") and record["best_rank"] <= place and record.get("best_rank_on"):
                out[i] = (record["best_rank_on"], False)
        return out
    if badge == "votes":
        votes = data["votes"].get(uid, [])
        return [(votes[n - 1].date(), False) if len(votes) >= n else None for n in t]
    return [None] * len(t)


def _raw_values(badge: str, value) -> tuple:
    """(value, value2) stored for sorting and display: (place, hours) for the ranking, (hours, messages) for versatility."""
    if isinstance(value, tuple):
        return (float(value[0]) if isinstance(value[0], (int, float)) else None, float(value[1] or 0))
    return (float(value or 0), None)


# ------------------------------------------------------------------------------
# Refresh
# ------------------------------------------------------------------------------
def compute(now: datetime | None = None) -> tuple[list, list]:
    """(value rows, tier rows) of every member, from the profile's own badge code."""
    now = now or datetime.now(timezone.utc).replace(tzinfo=None)
    data = _inputs(now)
    hist = _history()
    value_rows, tier_rows = [], []
    for uid, (seconds, messages, server_count, first_activity) in data["totals"].items():
        if uid in data["bots"]:
            continue
        live = int(data["live"].get(uid, 0))
        stats = {
            "user_id": uid,
            "total_seconds": seconds + live,
            "total_message": messages,
            "rank": data["ranks"].get(uid, "Non classé"),
            "user_servers_stats": [None] * server_count,
            "total_time_last_30d": int(data["last30"].get(uid, 0)) + live,
            "raw_join_date": first_activity,
            "best_streak": _longest_run(hist["active"].get(uid, set())),
            "votes_total": len(data["votes"].get(uid, [])),
            "best_records": data["records"].get(uid, {}),
        }
        values, _records = badge_values(stats)
        for definition in BADGE_DEFS:
            badge = definition[0]
            fam = _family_badge(definition, values[badge], "en")
            v1, v2 = _raw_values(badge, values[badge])
            value_rows.append((uid, badge, fam["tier"], v1, v2, float(fam["progress_percent"]), now))
            if not fam["tier"]:
                continue
            days = _tier_days(badge, uid, data, hist, first_activity)
            last = None
            for tier in range(1, fam["tier"] + 1):
                found = days[tier - 1] if tier - 1 < len(days) else None
                tier_rows.append((uid, badge, tier, found, last))
                last = found
    return value_rows, tier_rows


def _longest_run(days: set) -> int:
    best = run = 0
    previous = None
    for day in sorted(days):
        run = run + 1 if previous and (day - previous).days == 1 else 1
        previous = day
        best = max(best, run)
    return best


def refresh(force: bool = False) -> bool:
    """Recompute every member's tiers and days. True when this worker did it (False: locked or done < 1 h ago)."""
    if not enabled():
        return False
    from psycopg2.extras import execute_values

    now = datetime.now(timezone.utc).replace(tzinfo=None)
    today = now.date()
    with db.connection_context():
        with db.atomic():
            if not db.execute_sql("SELECT pg_try_advisory_xact_lock(%s)", (LOCK_ID,)).fetchone()[0]:
                return False
            last = db.execute_sql("SELECT MAX(updated_at) FROM user_badge_values").fetchone()[0]
            if last and not force and now - last < timedelta(seconds=REFRESH_SECONDS - 300):
                return False
            started = time.monotonic()
            value_rows, tier_rows = compute(now)
            # Days already known: a tier the history cannot date keeps the day it was first seen
            known = {(u, b, t): (d, bt) for u, b, t, d, bt in
                     db.execute_sql("SELECT user_id, badge, tier, reached_on, before_tracking FROM user_badge_tiers").fetchall()}
            final, previous_day = [], {}
            for uid, badge, tier, found, _last in tier_rows:
                if found:
                    day, before = found
                else:
                    day, before = known.get((uid, badge, tier), (today, False))
                # A tier is never reached before the one under it
                prev = previous_day.get((uid, badge)) if tier > 1 else None
                if prev and day < prev[0]:
                    day, before = prev
                if before:
                    day = IMPORT_DAY
                previous_day[(uid, badge)] = (day, before)
                final.append((uid, badge, tier, day, before))
            cursor = db.cursor()
            cursor.execute("DELETE FROM user_badge_values")
            execute_values(cursor, "INSERT INTO user_badge_values (user_id, badge, tier, value, value2, progress, updated_at) VALUES %s",
                           value_rows, page_size=2000)
            cursor.execute("DELETE FROM user_badge_tiers")
            execute_values(cursor, "INSERT INTO user_badge_tiers (user_id, badge, tier, reached_on, before_tracking) VALUES %s",
                           final, page_size=2000)
            log.info("Badge tiers refreshed: %d values, %d tiers (%.1f s)", len(value_rows), len(final), time.monotonic() - started)
    return True


def init_badge_stats(app) -> None:
    """Create the tables now; the first fill and the hourly refresh run in a background thread."""
    global _thread_started
    ensure_tables()
    # The thread starts even if the tables are missing now: refresh() creates them once possible
    if _thread_started or app.config.get("TESTING"):
        return
    _thread_started = True

    def loop():
        time.sleep(FIRST_RUN_DELAY_SECONDS)
        while True:
            try:
                refresh()
            except Exception as e:  # never break the worker for the badge pages
                log.warning("Badge tiers refresh failed: %s", e)
            time.sleep(REFRESH_SECONDS)

    threading.Thread(target=loop, name="badge-stats", daemon=True).start()
