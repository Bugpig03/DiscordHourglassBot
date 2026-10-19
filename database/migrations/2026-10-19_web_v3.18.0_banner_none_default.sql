-- ==============================================================================
-- HOURGLASS - Web v3.18.0 - No banner by default
-- ==============================================================================
-- user_profile_settings only (table owned by the web app, unused by the bot).
-- A banner is now shown only when the member picked a gallery picture: every other row
-- (old 'auto' / 'gradient' modes, or 'image' without a picture) becomes 'none'.
--
-- The web app already reads those rows as 'none', so running this file is optional (it only
-- tidies the stored values). Safe to run several times.
--   psql -d <db> -f 2026-10-19_web_v3.18.0_banner_none_default.sql
-- ==============================================================================

ALTER TABLE user_profile_settings ALTER COLUMN banner_mode SET DEFAULT 'none';
UPDATE user_profile_settings SET banner_mode = 'none'
WHERE banner_mode <> 'none' AND NOT (banner_mode = 'image' AND banner_image IS NOT NULL);
