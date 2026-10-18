-- ==============================================================================
-- HOURGLASS - Web v3.14.0 - Admin page statistics (anonymous audience + Discord logins)
-- ==============================================================================
-- New tables owned by the web app (the bot never touches them); existing tables are not modified.
-- No IP address is stored: visitors are a daily salted hash, the salt is deleted the next day.
-- The web app also creates these tables on startup, so running this file is optional.
-- IF NOT EXISTS: safe to run several times.
--   psql -d <db> -f 2026-10-18_web_v3.14.0_admin_stats.sql
-- ==============================================================================

CREATE TABLE IF NOT EXISTS web_daily_salt (day DATE PRIMARY KEY, salt TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS web_pageviews_daily (day DATE NOT NULL, page_key VARCHAR(32) NOT NULL, views INTEGER NOT NULL DEFAULT 0, PRIMARY KEY (day, page_key));
CREATE TABLE IF NOT EXISTS web_visitors_daily (day DATE NOT NULL, visitor_hash CHAR(16) NOT NULL, is_mobile BOOLEAN NOT NULL DEFAULT FALSE, lang VARCHAR(4) NOT NULL DEFAULT 'fr', PRIMARY KEY (day, visitor_hash));
CREATE TABLE IF NOT EXISTS web_entity_views_daily (day DATE NOT NULL, kind VARCHAR(16) NOT NULL, entity_id VARCHAR(64) NOT NULL, views INTEGER NOT NULL DEFAULT 0, PRIMARY KEY (day, kind, entity_id));
CREATE TABLE IF NOT EXISTS web_referrers_daily (day DATE NOT NULL, domain VARCHAR(80) NOT NULL, views INTEGER NOT NULL DEFAULT 0, PRIMARY KEY (day, domain));
CREATE TABLE IF NOT EXISTS web_hourly_views (day DATE NOT NULL, hour SMALLINT NOT NULL, views INTEGER NOT NULL DEFAULT 0, PRIMARY KEY (day, hour));
CREATE TABLE IF NOT EXISTS web_status_daily (day DATE NOT NULL, status SMALLINT NOT NULL, path_key VARCHAR(80) NOT NULL, hits INTEGER NOT NULL DEFAULT 0, PRIMARY KEY (day, status, path_key));
CREATE TABLE IF NOT EXISTS web_searches_daily (day DATE NOT NULL, term VARCHAR(40) NOT NULL, hits INTEGER NOT NULL DEFAULT 0, PRIMARY KEY (day, term));
CREATE TABLE IF NOT EXISTS web_accounts (user_id BIGINT PRIMARY KEY, first_login_at TIMESTAMP WITHOUT TIME ZONE NOT NULL, last_login_at TIMESTAMP WITHOUT TIME ZONE NOT NULL, login_count INTEGER NOT NULL DEFAULT 1);
CREATE TABLE IF NOT EXISTS web_logins_daily (day DATE NOT NULL, user_id BIGINT NOT NULL, PRIMARY KEY (day, user_id));

-- Accounts already known from the profile settings created at each Discord login since v3.3.0
INSERT INTO web_accounts (user_id, first_login_at, last_login_at, login_count)
SELECT user_id, updated_at, updated_at, 1 FROM user_profile_settings ON CONFLICT DO NOTHING;
