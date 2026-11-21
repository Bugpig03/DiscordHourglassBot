-- bot v3.11.0 + web v3.46.0: automatic roles (server management > Roles). Created automatically at startup by both
-- the bot (database/roles.go) and the website (app/server_admin.py), same definitions.

-- Switches of each server, written by the website
CREATE TABLE IF NOT EXISTS server_roles (
    server_id BIGINT PRIMARY KEY,
    enabled BOOLEAN NOT NULL DEFAULT FALSE,
    keep_highest BOOLEAN NOT NULL DEFAULT FALSE,    -- tiers: only the role of the last rule met is kept
    remove_unmet BOOLEAN NOT NULL DEFAULT TRUE,     -- a role the bot gave is removed when its rule is no longer met
    updated_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT NOW(),
    updated_by BIGINT
);

-- Rules, in the order of the page (easiest first): a role and 1 to 3 conditions (JSON list of
-- {"metric": "voice" | "messages" | "level", "scope": "total" | "30d", "min": n}), all of them or at least one
CREATE TABLE IF NOT EXISTS server_role_rules (
    id BIGSERIAL PRIMARY KEY,
    server_id BIGINT NOT NULL,
    position INTEGER NOT NULL DEFAULT 0,
    role_id BIGINT NOT NULL,
    match VARCHAR(3) NOT NULL DEFAULT 'all',        -- all (AND) / any (OR)
    conditions TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS server_role_rules_server ON server_role_rules (server_id, position);

-- Roles the bot gave itself: the only ones it may remove (a role given by hand is never touched)
CREATE TABLE IF NOT EXISTS role_grants (
    server_id BIGINT NOT NULL,
    user_id BIGINT NOT NULL,
    role_id BIGINT NOT NULL,
    granted_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT NOW(),
    PRIMARY KEY (server_id, user_id, role_id)
);
