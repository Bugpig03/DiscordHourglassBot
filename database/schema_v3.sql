-- ==============================================================================
-- HOURGLASS v3.0 - NOUVEAU SCHÉMA DE BASE DE DONNÉES
-- ==============================================================================
-- Ce script crée les nouvelles tables requises pour le tracking granulaire par
-- sessions vocales, salons (channels), messages horodatés et statut en direct.
-- Les tables existantes (users, servers, stats, historical_stats) sont préservées.
-- ==============================================================================

-- 1. Table des salons Discord (Vocaux, Textuels, Stages, etc.)
CREATE TABLE IF NOT EXISTS channels (
    channel_id BIGINT PRIMARY KEY,
    server_id BIGINT NOT NULL,
    name VARCHAR(255) NOT NULL,
    type VARCHAR(50) NOT NULL, -- 'voice', 'text', 'stage', 'category', etc.
    last_updated TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_channels_server ON channels(server_id);
CREATE INDEX IF NOT EXISTS idx_channels_type ON channels(type);

-- 2. Table des sessions vocales
CREATE TABLE IF NOT EXISTS voice_sessions (
    session_id BIGSERIAL PRIMARY KEY,
    user_id BIGINT NOT NULL,
    server_id BIGINT NOT NULL,
    channel_id BIGINT,                      -- NULL pour les sessions d'archive historique
    joined_at TIMESTAMP WITHOUT TIME ZONE NOT NULL,
    left_at TIMESTAMP WITHOUT TIME ZONE,    -- NULL tant que la session est en cours (LIVE)
    duration_seconds INTEGER DEFAULT 0,
    last_heartbeat TIMESTAMP WITHOUT TIME ZONE,
    is_legacy BOOLEAN DEFAULT FALSE,        -- TRUE pour les sessions reconstituées de l'ancien historique
    is_streaming BOOLEAN DEFAULT FALSE,     -- Partage d'écran actif
    is_camera_on BOOLEAN DEFAULT FALSE      -- Webcam active
);

-- Index pour performances maximales des requêtes Dashboard et API
CREATE INDEX IF NOT EXISTS idx_voice_sessions_user_server ON voice_sessions(user_id, server_id);
CREATE INDEX IF NOT EXISTS idx_voice_sessions_server_channel ON voice_sessions(server_id, channel_id);
CREATE INDEX IF NOT EXISTS idx_voice_sessions_joined_at ON voice_sessions(joined_at);
CREATE INDEX IF NOT EXISTS idx_voice_sessions_active ON voice_sessions(left_at) WHERE left_at IS NULL;
-- Per-member / per-server period queries (web v3.2.0)
CREATE INDEX IF NOT EXISTS idx_voice_sessions_user_joined ON voice_sessions(user_id, joined_at);
CREATE INDEX IF NOT EXISTS idx_voice_sessions_server_joined ON voice_sessions(server_id, joined_at);

-- 3. Table des événements de messages horodatés par salon
CREATE TABLE IF NOT EXISTS message_events (
    event_id BIGSERIAL PRIMARY KEY,
    user_id BIGINT NOT NULL,
    server_id BIGINT NOT NULL,
    channel_id BIGINT,                      -- NULL pour les archives historiques
    created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    count INTEGER DEFAULT 1,                -- 1 pour un message live, > 1 pour les lots d'archive
    is_legacy BOOLEAN DEFAULT FALSE         -- TRUE pour les lots reconstitués du passé
);

CREATE INDEX IF NOT EXISTS idx_message_events_user_server ON message_events(user_id, server_id);
CREATE INDEX IF NOT EXISTS idx_message_events_created_at ON message_events(created_at);
CREATE INDEX IF NOT EXISTS idx_message_events_server_channel ON message_events(server_id, channel_id);
CREATE INDEX IF NOT EXISTS idx_message_events_user_created ON message_events(user_id, created_at);
CREATE INDEX IF NOT EXISTS idx_message_events_server_created ON message_events(server_id, created_at);

-- 4. Table du statut en direct des serveurs (Présence & vocal)
CREATE TABLE IF NOT EXISTS live_server_status (
    server_id BIGINT PRIMARY KEY,
    online_count INTEGER DEFAULT 0,
    idle_count INTEGER DEFAULT 0,
    dnd_count INTEGER DEFAULT 0,
    offline_count INTEGER DEFAULT 0,
    voice_count INTEGER DEFAULT 0,
    updated_at TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- 5. Table du statut individuel des utilisateurs
CREATE TABLE IF NOT EXISTS user_presence (
    user_id BIGINT PRIMARY KEY,
    status VARCHAR(50) DEFAULT 'offline',
    last_updated TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- 6. Table de l'historique de présence sur 48h
CREATE TABLE IF NOT EXISTS presence_history (
    id BIGSERIAL PRIMARY KEY,
    server_id BIGINT,                       -- NULL pour le cumul global
    online_count INTEGER DEFAULT 0,
    idle_count INTEGER DEFAULT 0,
    dnd_count INTEGER DEFAULT 0,
    offline_count INTEGER DEFAULT 0,
    recorded_at TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_presence_history_time ON presence_history(recorded_at);

-- 7. Ajout des colonnes de présence du bot sur les serveurs
ALTER TABLE servers ADD COLUMN IF NOT EXISTS is_bot_present BOOLEAN DEFAULT TRUE;
ALTER TABLE servers ADD COLUMN IF NOT EXISTS first_tracked_at TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP;
ALTER TABLE servers ADD COLUMN IF NOT EXISTS left_at TIMESTAMP WITHOUT TIME ZONE;

-- 8. Personnalisation des profils (site web uniquement, v3.3.0)
CREATE TABLE IF NOT EXISTS user_profile_settings (
    user_id BIGINT PRIMARY KEY,
    accent_color VARCHAR(16) NOT NULL DEFAULT 'sky',
    banner_mode VARCHAR(16) NOT NULL DEFAULT 'none',   -- none | image (auto / gradient: old values, read as none)
    discord_banner VARCHAR(64),
    discord_accent INTEGER,
    favorite_server_id BIGINT,
    banner_image VARCHAR(32),
    background_image VARCHAR(32),                      -- unused since web v3.17.0
    background_color VARCHAR(16),
    featured_badges TEXT NOT NULL DEFAULT '[]',
    pinned_records TEXT NOT NULL DEFAULT '[]',
    layout TEXT NOT NULL DEFAULT '{}',
    updated_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- 9. Statistiques de la page admin (site web uniquement, v3.14.0)
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

-- 10. Utilisation des commandes slash (bot v3.1.0, lue par la page admin du site)
CREATE TABLE IF NOT EXISTS bot_command_events (
    id BIGSERIAL PRIMARY KEY,
    command VARCHAR(32) NOT NULL,
    server_id BIGINT,
    options VARCHAR(120) NOT NULL DEFAULT '',
    success BOOLEAN NOT NULL DEFAULT TRUE,
    duration_ms INTEGER NOT NULL DEFAULT 0,
    created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_bot_command_events_created ON bot_command_events (created_at);

-- Unique members present on the servers, every 15 min (bot v3.3.0, admin page only, kept 90 days)
CREATE TABLE IF NOT EXISTS bot_member_snapshots (
    recorded_at TIMESTAMP WITHOUT TIME ZONE PRIMARY KEY DEFAULT NOW(),
    unique_members INTEGER NOT NULL,
    unique_online INTEGER NOT NULL,
    memberships INTEGER NOT NULL,
    servers INTEGER NOT NULL,
    known_members INTEGER NOT NULL
);
