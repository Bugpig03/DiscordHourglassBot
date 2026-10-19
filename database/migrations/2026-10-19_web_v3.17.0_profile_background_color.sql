-- ==============================================================================
-- HOURGLASS - Web v3.17.0 - Solid page background color, banner = gallery or none
-- ==============================================================================
-- user_profile_settings only (table owned by the web app, unused by the bot).
--   * new column background_color (replaces the removed background gallery);
--   * old banner modes 'auto' (Discord banner) and 'gradient' become 'image' (gallery);
--   * background_image is emptied (its pictures were removed from the site).
--
-- The web app adds the column on startup and already shows old modes as the gallery picture,
-- so running this file is optional (it only tidies the stored values). Safe to run several times.
--   psql -d <db> -f 2026-10-19_web_v3.17.0_profile_background_color.sql
-- ==============================================================================

ALTER TABLE user_profile_settings ADD COLUMN IF NOT EXISTS background_color VARCHAR(16);  -- key of BACKGROUND_COLORS
ALTER TABLE user_profile_settings ALTER COLUMN banner_mode SET DEFAULT 'image';
UPDATE user_profile_settings SET banner_mode = 'image' WHERE banner_mode NOT IN ('image', 'none');
UPDATE user_profile_settings SET background_image = NULL WHERE background_image IS NOT NULL;
