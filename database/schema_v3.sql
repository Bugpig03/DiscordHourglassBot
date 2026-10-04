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
