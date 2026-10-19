-- ==============================================================================
-- HOURGLASS - Web v3.18.1 - Indexes missing in production
-- ==============================================================================
-- The production backup of 19/10/2026 lacks four composite indexes declared in
-- schema_v3.sql. They speed up member and server pages (activity of one member / one
-- server over a period). IF NOT EXISTS: safe to run several times.
-- CONCURRENTLY: no table lock while building (do not wrap this file in a transaction).
--   psql -d <db> -f 2026-10-19_web_v3.18.1_missing_indexes.sql
-- ==============================================================================

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_voice_sessions_user_joined ON voice_sessions(user_id, joined_at);
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_voice_sessions_server_joined ON voice_sessions(server_id, joined_at);
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_message_events_user_created ON message_events(user_id, created_at);
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_message_events_server_created ON message_events(server_id, created_at);
