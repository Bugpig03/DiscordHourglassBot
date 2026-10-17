-- ==============================================================================
-- HOURGLASS - Web v3.2.0 - Composite indexes for per-member / per-server period queries
-- ==============================================================================
-- "Last 24 h / 7 days / period" figures filter by member or server AND by date. The existing
-- single-column indexes (joined_at, created_at, user_id+server_id) make PostgreSQL scan every
-- session of the period, then filter: the cost grows with total activity. These indexes go
-- straight to the rows of one member or one server.
--
-- CONCURRENTLY: built without locking the tables (the bot keeps writing). Run outside a
-- transaction block, e.g.:  psql -d <db> -f 2026-10-17_web_v3.2.0_indexes.sql
-- IF NOT EXISTS: safe to run several times.
-- ==============================================================================

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_voice_sessions_user_joined   ON voice_sessions (user_id, joined_at);
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_voice_sessions_server_joined ON voice_sessions (server_id, joined_at);
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_message_events_user_created   ON message_events (user_id, created_at);
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_message_events_server_created ON message_events (server_id, created_at);

-- Refresh planner statistics so the new indexes are picked up immediately
ANALYZE voice_sessions;
ANALYZE message_events;
