-- ==============================================================================
-- HOURGLASS - Web v3.23.0 - Real arrival date of the servers
-- ==============================================================================
-- servers.first_tracked_at was added in October 2026 with DEFAULT CURRENT_TIMESTAMP: every server
-- already known that day got the migration date (4 Oct 2026). This sets it back to the first stats
-- row of the server when that is older. Only ever moves dates earlier; safe to run several times.
-- Optional: the website already shows the corrected date without it.
--   psql -d <db> -f 2026-10-23_web_v3.23.0_server_first_tracked_fix.sql
-- ==============================================================================

UPDATE servers s
SET first_tracked_at = f.first
FROM (SELECT server_id, MIN(date_creation) AS first FROM stats GROUP BY server_id) f
WHERE f.server_id = s.server_id
  AND f.first IS NOT NULL
  AND (s.first_tracked_at IS NULL OR f.first < s.first_tracked_at);
