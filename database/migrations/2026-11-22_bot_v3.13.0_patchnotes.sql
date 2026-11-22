-- bot v3.13.0 + web v3.49.0: patch notes on the official Discord server (admin page > Patch notes). Created
-- automatically at startup by both the bot (database/patchnotes.go) and the website (app/patchnotes.py).

-- The settings (a single row, id = 1), written by the admin page
CREATE TABLE IF NOT EXISTS patchnote_settings (
    id SMALLINT PRIMARY KEY DEFAULT 1,
    enabled BOOLEAN NOT NULL DEFAULT FALSE,
    server_id BIGINT,
    channel_id BIGINT,
    scope VARCHAR(8) NOT NULL DEFAULT 'both',      -- both, web, bot
    mention_role_id BIGINT,
    since TIMESTAMP WITHOUT TIME ZONE,              -- turned on at: only the versions that arrive after are posted
    updated_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT NOW(),
    updated_by BIGINT
);

-- Every version of the website and of the bot, written by each at startup from its own CHANGELOG (French) and
-- CHANGELOG.en.md (English)
CREATE TABLE IF NOT EXISTS patchnotes (
    id BIGSERIAL PRIMARY KEY,
    component VARCHAR(8) NOT NULL,                  -- web, bot
    version VARCHAR(32) NOT NULL,
    title TEXT NOT NULL DEFAULT '',
    released VARCHAR(10),
    body TEXT NOT NULL,
    created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT NOW(),
    requested_at TIMESTAMP WITHOUT TIME ZONE,       -- "post the latest version now" from the admin page
    posted_at TIMESTAMP WITHOUT TIME ZONE,          -- booked before posting: never posted twice
    ok BOOLEAN,
    detail TEXT,
    baseline BOOLEAN NOT NULL DEFAULT FALSE,        -- written by the very first startup: already known, never posted
    title_en TEXT NOT NULL DEFAULT '',              -- English entry (CHANGELOG.en.md), posted first; empty: French only
    body_en TEXT NOT NULL DEFAULT '',
    UNIQUE (component, version)
);
