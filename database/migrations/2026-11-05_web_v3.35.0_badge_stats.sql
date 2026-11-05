-- web v3.35.0: badge pages (/badge/<id>). Website tables only, also created automatically at startup
-- (app/badge_stats.py) and refilled every hour from the history.

-- Each member's tier, measured value and progress toward the next tier, for every badge
CREATE TABLE IF NOT EXISTS user_badge_values (
    user_id BIGINT NOT NULL,
    badge VARCHAR(16) NOT NULL,                -- voice, messages, level, rank, servers, loyalty, activity, streak, hybrid, votes
    tier SMALLINT NOT NULL,                    -- 0 (none) to 7 (Mythic)
    value DOUBLE PRECISION,                    -- hours, messages, level, best place (rank), servers, days, votes
    value2 DOUBLE PRECISION,                   -- second figure: hours at the best place (rank), messages (versatility)
    progress REAL NOT NULL DEFAULT 0,          -- % toward the next tier (100 at Mythic)
    updated_at TIMESTAMP WITHOUT TIME ZONE NOT NULL,
    PRIMARY KEY (user_id, badge)
);
CREATE INDEX IF NOT EXISTS user_badge_values_badge_tier ON user_badge_values (badge, tier);

-- The day each reached tier was reached
CREATE TABLE IF NOT EXISTS user_badge_tiers (
    user_id BIGINT NOT NULL,
    badge VARCHAR(16) NOT NULL,
    tier SMALLINT NOT NULL,
    reached_on DATE NOT NULL,
    before_tracking BOOLEAN NOT NULL DEFAULT FALSE, -- already reached on 5 Oct 2024 (the old bot only kept totals)
    PRIMARY KEY (user_id, badge, tier)
);
CREATE INDEX IF NOT EXISTS user_badge_tiers_badge_reached ON user_badge_tiers (badge, reached_on DESC);
