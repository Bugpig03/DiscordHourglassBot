-- ==============================================================================
-- HOURGLASS - Web v3.3.0 - Profile customization table
-- ==============================================================================
-- Stores what each member chooses on /me/profile (accent color, banner, favorite server,
-- featured badges, pinned records, block layout). Only the web app reads and writes it;
-- the bot never touches it. Adds a new table: existing tables and data are not modified.
--
-- The web app also creates this table on startup if it is missing, so running this file
-- is optional. IF NOT EXISTS: safe to run several times.
--   psql -d <db> -f 2026-10-17_web_v3.3.0_profile_settings.sql
-- ==============================================================================

CREATE TABLE IF NOT EXISTS user_profile_settings (
    user_id BIGINT PRIMARY KEY,
    accent_color VARCHAR(16) NOT NULL DEFAULT 'sky',
    banner_mode VARCHAR(16) NOT NULL DEFAULT 'auto',   -- auto (Discord banner, else gradient) | gradient | none
    discord_banner VARCHAR(64),                        -- banner hash seen at the last Discord login
    discord_accent INTEGER,                            -- Discord profile color seen at the last login
    favorite_server_id BIGINT,
    featured_badges TEXT NOT NULL DEFAULT '[]',        -- JSON list of badge ids (max 3)
    pinned_records TEXT NOT NULL DEFAULT '[]',         -- JSON list of record keys (max 4)
    layout TEXT NOT NULL DEFAULT '{}',                 -- JSON {"order": [...], "hidden": [...]}
    updated_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP
);
