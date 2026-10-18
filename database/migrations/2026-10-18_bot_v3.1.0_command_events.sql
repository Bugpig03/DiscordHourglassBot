-- ==============================================================================
-- HOURGLASS - Bot v3.1.0 - Slash command usage (shown on the website admin page)
-- ==============================================================================
-- New table written by the bot for each slash command: command name, server (NULL in DMs),
-- choice options (type / period / scope), success and duration. No member identifier is stored.
-- Rows older than 90 days are purged by the bot. Existing tables are not modified.
--
-- The bot also creates this table on startup, so running this file is optional.
-- IF NOT EXISTS: safe to run several times.
--   psql -d <db> -f 2026-10-18_bot_v3.1.0_command_events.sql
-- ==============================================================================

CREATE TABLE IF NOT EXISTS bot_command_events (
    id BIGSERIAL PRIMARY KEY,
    command VARCHAR(32) NOT NULL,
    server_id BIGINT,
    options VARCHAR(120) NOT NULL DEFAULT '',
    success BOOLEAN NOT NULL DEFAULT TRUE,
    duration_ms INTEGER NOT NULL DEFAULT 0,
    created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_bot_command_events_created ON bot_command_events (created_at);
