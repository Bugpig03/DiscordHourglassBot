"""Best global rank and best 30-day voice activity of every member, kept so the Ranking and Activity badges
never go down (the badges themselves are still computed live, see gamification.calculate_user_badges).

Table user_best_records (web side only, no bot table is touched), one row per member:
  - best_rank / best_rank_on: best spot in the global voice ranking (bots and apps left out) and the first day it
    was reached; best_rank_hours: the most voice hours held at that spot (shown for information);
  - best_30d_seconds / best_30d_end: most voice time over 30 sliding days and the last day of that window.
A record only ever improves. On creation the table is filled from the history: the daily snapshots of
historical_stats (ranks since October 2024) and voice_sessions (30-day windows). Then one worker refreshes every
member once an hour, under a database lock so the Gunicorn workers never do it twice.
"""

import logging
import threading
import time
from datetime import date, datetime, timedelta, timezone

from peewee import DatabaseError

from app.cache import cache
from app.database import db

log = logging.getLogger(__name__)

REFRESH_SECONDS = 3600
FIRST_RUN_DELAY_SECONDS = 45  # after startup, so the backfill never slows a deploy
CACHE_SECONDS = 300
LOCK_ID = 727301  # pg advisory lock of the refresh (any constant unique to this job)

TABLE = ("CREATE TABLE IF NOT EXISTS user_best_records (user_id BIGINT PRIMARY KEY, best_rank INTEGER, best_rank_on DATE, "
         "best_rank_hours REAL, best_30d_seconds BIGINT, best_30d_end DATE, updated_at TIMESTAMP WITHOUT TIME ZONE NOT NULL)")

# Upserts that only keep better values. Rank: a lower spot wins (its date is the day it was first reached); at the
# same spot only the hours grow. Activity: more seconds win, with the end day of that window.
UPSERT_RANK = """
INSERT INTO user_best_records (user_id, best_rank, best_rank_on, best_rank_hours, updated_at) VALUES (%s, %s, %s, %s, %s)
ON CONFLICT (user_id) DO UPDATE SET
    best_rank_on = CASE WHEN user_best_records.best_rank IS NULL OR EXCLUDED.best_rank < user_best_records.best_rank
                        THEN EXCLUDED.best_rank_on ELSE user_best_records.best_rank_on END,
    best_rank_hours = CASE WHEN user_best_records.best_rank IS NULL OR EXCLUDED.best_rank < user_best_records.best_rank
                           THEN EXCLUDED.best_rank_hours
                           WHEN EXCLUDED.best_rank = user_best_records.best_rank
                           THEN GREATEST(EXCLUDED.best_rank_hours, user_best_records.best_rank_hours)
                           ELSE user_best_records.best_rank_hours END,
    best_rank = LEAST(EXCLUDED.best_rank, COALESCE(user_best_records.best_rank, EXCLUDED.best_rank)),
    updated_at = EXCLUDED.updated_at
"""
UPSERT_ACTIVITY = """
INSERT INTO user_best_records (user_id, best_30d_seconds, best_30d_end, updated_at) VALUES (%s, %s, %s, %s)
ON CONFLICT (user_id) DO UPDATE SET
    best_30d_end = CASE WHEN user_best_records.best_30d_seconds IS NULL OR EXCLUDED.best_30d_seconds > user_best_records.best_30d_seconds
                        THEN EXCLUDED.best_30d_end ELSE user_best_records.best_30d_end END,
    best_30d_seconds = GREATEST(EXCLUDED.best_30d_seconds, COALESCE(user_best_records.best_30d_seconds, 0)),
    updated_at = EXCLUDED.updated_at
"""

# Bots and apps are left out of the ranking (users.is_bot, set by the bot since v3.4.0; absent: nobody left out)
_HUMANS = "user_id NOT IN (SELECT user_id FROM users WHERE is_bot)"

# Rank of every member on every day of history: the last snapshot of each day, total voice over all servers
HISTORY_RANKS = """
WITH snap AS (
    SELECT DISTINCT ON (created_at::date, user_id, server_id) created_at::date AS day, user_id, seconds
    FROM historical_stats WHERE user_id IS NOT NULL {humans}
    ORDER BY created_at::date, user_id, server_id, created_at DESC
), totals AS (
    SELECT day, user_id, SUM(seconds) AS s FROM snap GROUP BY day, user_id HAVING SUM(seconds) > 0
), ranked AS (
    SELECT day, user_id, s, RANK() OVER (PARTITION BY day ORDER BY s DESC) AS r FROM totals
), best AS (
    SELECT user_id, MIN(r) AS r FROM ranked GROUP BY user_id
)
SELECT b.user_id, b.r, MIN(k.day), MAX(k.s) / 3600.0
FROM best b JOIN ranked k ON k.user_id = b.user_id AND k.r = b.r
GROUP BY b.user_id, b.r
"""

# Best 30 sliding days of voice of every member, from the finished voice sessions. Left out: the totals imported
# when voice_sessions was created (5 Oct 2024), stored as zero-length sessions of up to 257 h; and a day never
# counts more than 24 h.
HISTORY_ACTIVITY = """
WITH daily AS (
    SELECT user_id, joined_at::date AS day, LEAST(SUM(duration_seconds), 86400) AS s
    FROM voice_sessions
    WHERE duration_seconds > 0 AND NOT (left_at = joined_at AND duration_seconds > 86400)
    GROUP BY user_id, joined_at::date
), windows AS (
    SELECT user_id, day, SUM(s) OVER (PARTITION BY user_id ORDER BY day
                                      RANGE BETWEEN INTERVAL '29 days' PRECEDING AND CURRENT ROW) AS total
    FROM daily
)
SELECT DISTINCT ON (user_id) user_id, total, day FROM windows ORDER BY user_id, total DESC, day ASC
"""

CURRENT_RANKS = """
SELECT user_id, RANK() OVER (ORDER BY SUM(seconds) DESC), SUM(seconds) / 3600.0
FROM stats WHERE TRUE {humans} GROUP BY user_id HAVING SUM(seconds) > 0
"""
CURRENT_ACTIVITY = """
SELECT user_id, SUM(duration_seconds) FROM voice_sessions WHERE joined_at >= %s AND duration_seconds > 0 GROUP BY user_id
"""

_enabled = True
_thread_started = False


def _has_bot_column() -> bool:
    row = db.execute_sql("SELECT 1 FROM information_schema.columns WHERE table_name = 'users' AND column_name = 'is_bot'").fetchone()
    return bool(row)


def ensure_table() -> None:
    global _enabled
    try:
        with db.connection_context():
            db.execute_sql(TABLE)
    except DatabaseError as e:
        _enabled = False
        log.warning("Best records disabled (table unavailable, run the web migrations): %s", e)


def refresh(force: bool = False) -> bool:
    """Fill the table from the history if it is empty, then store the current ranks and 30 days when better.

    Returns True when this worker did the work (False: another one holds the lock or did it less than an hour ago).
    """
    if not _enabled:
        return False
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    today = now.date()
    with db.connection_context():
        with db.atomic():
            if not db.execute_sql("SELECT pg_try_advisory_xact_lock(%s)", (LOCK_ID,)).fetchone()[0]:
                return False
            last = db.execute_sql("SELECT MAX(updated_at) FROM user_best_records").fetchone()[0]
            if last and not force and now - last < timedelta(seconds=REFRESH_SECONDS - 300):
                return False
            humans = f"AND {_HUMANS}" if _has_bot_column() else ""
            cursor = db.cursor()
            if last is None:  # first run: the whole history
                started = time.monotonic()
                ranks = db.execute_sql(HISTORY_RANKS.format(humans=humans)).fetchall()
                cursor.executemany(UPSERT_RANK, [(uid, int(r), day, float(h), now) for uid, r, day, h in ranks])
                activity = db.execute_sql(HISTORY_ACTIVITY).fetchall()
                cursor.executemany(UPSERT_ACTIVITY, [(uid, int(s), day, now) for uid, s, day in activity])
                log.info("Best records filled from the history: %d ranks, %d activity windows (%.1f s)",
                         len(ranks), len(activity), time.monotonic() - started)
            ranks = db.execute_sql(CURRENT_RANKS.format(humans=humans)).fetchall()
            cursor.executemany(UPSERT_RANK, [(uid, int(r), today, float(h), now) for uid, r, h in ranks])
            activity = db.execute_sql(CURRENT_ACTIVITY, (now - timedelta(days=30),)).fetchall()
            cursor.executemany(UPSERT_ACTIVITY, [(uid, int(s), today, now) for uid, s in activity])
    return True


def get_best_records(user_id: int | str) -> dict | None:
    """The member's records (cached 5 min), or None when none is known yet."""
    if not _enabled or not str(user_id).isdigit():
        return None

    def load():
        try:
            row = db.execute_sql(
                "SELECT best_rank, best_rank_on, best_rank_hours, best_30d_seconds, best_30d_end FROM user_best_records WHERE user_id = %s",
                (int(user_id),)).fetchone()
        except DatabaseError:
            db.rollback()
            return None
        if not row:
            return None
        rank, rank_on, rank_hours, seconds, end = row
        return {
            "best_rank": rank, "best_rank_on": rank_on, "best_rank_hours": float(rank_hours or 0),
            "best_30d_hours": (seconds or 0) / 3600.0, "best_30d_end": end,
            "best_30d_start": end - timedelta(days=29) if isinstance(end, date) else None,
        }

    return cache.get_or_set(("best_records", int(user_id)), CACHE_SECONDS, load)


def init_best_records(app) -> None:
    """Create the table now; the history backfill and the hourly refresh run in a background thread."""
    global _thread_started
    ensure_table()
    if not _enabled or _thread_started or app.config.get("TESTING"):
        return
    _thread_started = True

    def loop():
        time.sleep(FIRST_RUN_DELAY_SECONDS)
        while True:
            try:
                refresh()
            except Exception as e:  # never break the worker for the records
                log.warning("Best records refresh failed: %s", e)
            time.sleep(REFRESH_SECONDS)

    threading.Thread(target=loop, name="best-records", daemon=True).start()
