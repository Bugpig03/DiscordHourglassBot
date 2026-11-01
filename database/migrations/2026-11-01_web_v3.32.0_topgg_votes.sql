-- web v3.32.0: votes for Hourglass on top.gg (also created automatically by the site at startup).
-- Filled by the webhook /webhooks/topgg (TOPGG_WEBHOOK_SECRET) and caught up every hour from the top.gg API (TOPGG_TOKEN).
-- Read by the site (Supporter badge, profile, admin) and by the bot (/vote, bot v3.6.0).
CREATE TABLE IF NOT EXISTS topgg_votes (
    user_id BIGINT NOT NULL,                        -- voter's Discord ID
    created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL, -- when they voted (UTC, to the second)
    expires_at TIMESTAMP WITHOUT TIME ZONE,          -- when they can vote again (12 h later)
    weight SMALLINT NOT NULL DEFAULT 1,              -- 2 on weekends (the badge counts votes, not weight)
    source VARCHAR(8) NOT NULL,                      -- webhook or api
    PRIMARY KEY (user_id, created_at)
);
CREATE INDEX IF NOT EXISTS topgg_votes_created ON topgg_votes (created_at);
