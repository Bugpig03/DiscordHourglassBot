-- ==============================================================================
-- HOURGLASS - Bot v3.4.0 / Web v3.26.0 - Bot and app accounts flagged in users
-- ==============================================================================
-- users.is_bot is TRUE for Discord bots and apps (music bots in voice, for example). The website shows a
-- "BOT" tag after their name and hides them from its member rankings by default.
-- The bot sets it when it records a member, and flags the bots present on its servers every 15 minutes
-- (so the bots recorded before this version are flagged too).
--
-- The bot adds this column on startup, so running this file is optional. Safe to run several times.
--   psql -d <db> -f 2026-10-30_bot_v3.4.0_users_is_bot.sql
-- ==============================================================================

ALTER TABLE users ADD COLUMN IF NOT EXISTS is_bot BOOLEAN NOT NULL DEFAULT FALSE;
