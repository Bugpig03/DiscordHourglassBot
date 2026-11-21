-- bot v3.12.0 + web v3.47.0: automatic roles by progressions. A rule now holds several tiers (one role each), and
-- chooses itself whether to keep the highest tier reached or stack them. Created automatically at startup by both
-- the bot (database/roles.go) and the website (app/server_admin.py), same definitions.

-- The rules of a server, in the order of the page
CREATE TABLE IF NOT EXISTS server_role_ladders (
    id BIGSERIAL PRIMARY KEY,
    server_id BIGINT NOT NULL,
    position INTEGER NOT NULL DEFAULT 0,
    keep_highest BOOLEAN NOT NULL DEFAULT TRUE      -- only the role of the last tier reached (else every tier reached)
);
CREATE INDEX IF NOT EXISTS server_role_ladders_server ON server_role_ladders (server_id, position);

-- The tiers of each rule, easiest first: a role and 1 to 3 conditions (same JSON as server_role_rules)
CREATE TABLE IF NOT EXISTS server_role_tiers (
    id BIGSERIAL PRIMARY KEY,
    ladder_id BIGINT NOT NULL,
    server_id BIGINT NOT NULL,
    position INTEGER NOT NULL DEFAULT 0,
    role_id BIGINT NOT NULL,
    match VARCHAR(3) NOT NULL DEFAULT 'all',
    conditions TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS server_role_tiers_server ON server_role_tiers (server_id, ladder_id, position);

-- The rules of v3.11.0 (server_role_rules, one role each) are turned by the bot at startup into one rule per server
-- holding them as tiers, with the server's former choice (server_roles.keep_highest); server_role_rules then stays
-- empty and server_roles.keep_highest is no longer read.
