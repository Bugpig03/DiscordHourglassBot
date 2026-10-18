-- ==============================================================================
-- HOURGLASS - Bot v3.1.1 - presence_history cleanup (per-server snapshots removed)
-- ==============================================================================
-- The bot stored one presence row per server every 15 minutes (kept 7 days): with many servers
-- this reached millions of rows (~250 MB) although the website only reads the global snapshot
-- (server_id IS NULL). From v3.1.1 the bot stores the global snapshot only, and deletes the
-- per-server rows itself at startup (in batches).
--
-- Run this AFTER deploying bot v3.1.1, once, to give the disk space back to the system:
--   psql -d <db> -f 2026-10-18_bot_v3.1.1_presence_history_cleanup.sql
-- VACUUM FULL rewrites the (now tiny) table and locks it for a moment: the bot retries its next
-- snapshot 15 minutes later, nothing is lost. It cannot run inside a transaction block.
-- ==============================================================================

DELETE FROM presence_history WHERE server_id IS NOT NULL;
VACUUM FULL ANALYZE presence_history;
