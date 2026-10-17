-- ==============================================================================
-- HOURGLASS - Web v3.9.0 - Gallery pictures for profile banners and backgrounds
-- ==============================================================================
-- Adds two nullable columns to user_profile_settings (table owned by the web app, unused by
-- the bot). Existing rows and other tables are not modified.
--
-- The web app also adds these columns on startup when they are missing, so running this file
-- is optional. IF NOT EXISTS: safe to run several times.
--   psql -d <db> -f 2026-10-17_web_v3.9.0_profile_images.sql
-- ==============================================================================

ALTER TABLE user_profile_settings ADD COLUMN IF NOT EXISTS banner_image VARCHAR(32);      -- gallery key when banner_mode = 'image'
ALTER TABLE user_profile_settings ADD COLUMN IF NOT EXISTS background_image VARCHAR(32);  -- gallery key of the page background
