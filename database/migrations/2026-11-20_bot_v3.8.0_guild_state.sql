-- bot v3.8.0: copy of each server for the website (server management page). Bot tables, also created automatically
-- at startup (database/guild_state.go). Written by the bot, read by the website: it never needs the bot token.

-- Owner, language and the bot's own permissions on each server
CREATE TABLE IF NOT EXISTS guild_meta (
    server_id BIGINT PRIMARY KEY,
    owner_id BIGINT,
    locale VARCHAR(16),
    bot_permissions BIGINT NOT NULL DEFAULT 0,          -- server-wide permission bits of the bot
    bot_top_role_position INTEGER NOT NULL DEFAULT 0,   -- the bot can only give roles below this position
    member_count INTEGER NOT NULL DEFAULT 0,
    bot_present BOOLEAN NOT NULL DEFAULT TRUE,          -- FALSE once removed: the copy and settings are kept
    synced_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT NOW(),
    members_synced_at TIMESTAMP WITHOUT TIME ZONE
);
CREATE INDEX IF NOT EXISTS guild_meta_owner ON guild_meta (owner_id);

-- Text and announcement channels, and what the bot may do in each
CREATE TABLE IF NOT EXISTS guild_channels (
    server_id BIGINT NOT NULL,
    channel_id BIGINT NOT NULL,
    name VARCHAR(100) NOT NULL,
    kind VARCHAR(16) NOT NULL,                          -- text, announcement
    category VARCHAR(100),
    position INTEGER NOT NULL DEFAULT 0,
    can_view BOOLEAN NOT NULL DEFAULT FALSE,
    can_send BOOLEAN NOT NULL DEFAULT FALSE,
    can_embed BOOLEAN NOT NULL DEFAULT FALSE,
    can_attach BOOLEAN NOT NULL DEFAULT FALSE,
    PRIMARY KEY (server_id, channel_id)
);

-- Roles (without @everyone): assignable by the bot, or dangerous (administration, moderation)
CREATE TABLE IF NOT EXISTS guild_roles (
    server_id BIGINT NOT NULL,
    role_id BIGINT NOT NULL,
    name VARCHAR(100) NOT NULL,
    color INTEGER NOT NULL DEFAULT 0,
    position INTEGER NOT NULL DEFAULT 0,
    managed BOOLEAN NOT NULL DEFAULT FALSE,
    permissions BIGINT NOT NULL DEFAULT 0,
    assignable BOOLEAN NOT NULL DEFAULT FALSE,
    dangerous BOOLEAN NOT NULL DEFAULT FALSE,
    PRIMARY KEY (server_id, role_id)
);

-- Current members of each server (bots left out): server managers and private mode rely on it
CREATE TABLE IF NOT EXISTS guild_members (
    server_id BIGINT NOT NULL,
    user_id BIGINT NOT NULL,
    username VARCHAR(100),
    display_name VARCHAR(100),
    avatar TEXT,
    joined_at TIMESTAMP WITHOUT TIME ZONE,
    PRIMARY KEY (server_id, user_id)
);
CREATE INDEX IF NOT EXISTS guild_members_user ON guild_members (user_id);

-- Journal of the server management features (also written by the website)
CREATE TABLE IF NOT EXISTS server_feature_log (
    id BIGSERIAL PRIMARY KEY,
    server_id BIGINT NOT NULL,
    created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT NOW(),
    feature VARCHAR(16) NOT NULL,                       -- general, levels, reports, roles
    action VARCHAR(32) NOT NULL,
    actor_id BIGINT,
    target_id BIGINT,
    ok BOOLEAN NOT NULL DEFAULT TRUE,
    detail TEXT
);
CREATE INDEX IF NOT EXISTS server_feature_log_server ON server_feature_log (server_id, created_at DESC);
CREATE INDEX IF NOT EXISTS server_feature_log_created ON server_feature_log (created_at);
