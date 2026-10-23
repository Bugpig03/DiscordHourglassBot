-- ==============================================================================
-- HOURGLASS - Bot v3.3.0 - Unique members present on the servers (admin page)
-- ==============================================================================
-- Every 15 minutes the bot stores how many distinct people are on its servers (each person counted
-- once, bots excluded), how many are online, and how many already have recorded activity.
-- Shown on the website admin page only. Rows older than 90 days are deleted by the bot.
--
-- The bot creates this table on startup, so running this file is optional. Safe to run several times.
--   psql -d <db> -f 2026-10-23_bot_v3.3.0_member_snapshots.sql
-- ==============================================================================

CREATE TABLE IF NOT EXISTS bot_member_snapshots (
    recorded_at TIMESTAMP WITHOUT TIME ZONE PRIMARY KEY DEFAULT NOW(),
    unique_members INTEGER NOT NULL,   -- distinct members across every server
    unique_online INTEGER NOT NULL,    -- of which online, idle or do not disturb
    memberships INTEGER NOT NULL,      -- member x server pairs
    servers INTEGER NOT NULL,          -- servers whose member list was available
    known_members INTEGER NOT NULL     -- of the unique members, those with recorded activity
);
