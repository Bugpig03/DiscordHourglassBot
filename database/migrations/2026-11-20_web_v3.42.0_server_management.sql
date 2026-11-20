-- web v3.42.0: server management (owner of a Discord server and the managers they choose). Website tables, also
-- created automatically at startup (app/server_admin.py). Applied by the bot: settings of each server.

CREATE TABLE IF NOT EXISTS server_settings (
    server_id BIGINT PRIMARY KEY,
    timezone VARCHAR(64) NOT NULL DEFAULT 'Europe/Paris', -- IANA zone: hour of the reports, end of the days
    private BOOLEAN NOT NULL DEFAULT FALSE,              -- private mode (detailed stats for the members only)
    updated_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT NOW(),
    updated_by BIGINT
);

-- Members the owner chose to manage the server (rights only while they are still members)
CREATE TABLE IF NOT EXISTS server_managers (
    server_id BIGINT NOT NULL,
    user_id BIGINT NOT NULL,
    added_by BIGINT,
    added_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT NOW(),
    PRIMARY KEY (server_id, user_id)
);
CREATE INDEX IF NOT EXISTS server_managers_user ON server_managers (user_id);

-- Shared with the bot (same definition in 2026-11-20_bot_v3.8.0_guild_state.sql)
CREATE TABLE IF NOT EXISTS server_feature_log (
    id BIGSERIAL PRIMARY KEY,
    server_id BIGINT NOT NULL,
    created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT NOW(),
    feature VARCHAR(16) NOT NULL,
    action VARCHAR(32) NOT NULL,
    actor_id BIGINT,
    target_id BIGINT,
    ok BOOLEAN NOT NULL DEFAULT TRUE,
    detail TEXT
);
CREATE INDEX IF NOT EXISTS server_feature_log_server ON server_feature_log (server_id, created_at DESC);
CREATE INDEX IF NOT EXISTS server_feature_log_created ON server_feature_log (created_at);
