-- web v3.30.0: best global rank and best 30-day voice activity of each member, so the Ranking and Activity
-- badges never go down. Also created automatically by the site at startup, which fills it from the history
-- (historical_stats daily snapshots and voice_sessions) on first run, then refreshes it every hour.
CREATE TABLE IF NOT EXISTS user_best_records (
    user_id BIGINT PRIMARY KEY,
    best_rank INTEGER,               -- best spot in the global voice ranking (bots and apps left out)
    best_rank_on DATE,               -- first day that spot was reached
    best_rank_hours REAL,            -- most voice hours held at that spot (for information)
    best_30d_seconds BIGINT,         -- most voice time over 30 sliding days
    best_30d_end DATE,               -- last day of that 30-day window
    updated_at TIMESTAMP WITHOUT TIME ZONE NOT NULL
);
