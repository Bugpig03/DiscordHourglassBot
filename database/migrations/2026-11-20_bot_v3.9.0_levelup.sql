-- bot v3.9.0 + web v3.43.0: level-up announcements (server management > Levels). Created automatically at startup by
-- both the bot (database/levelup.go) and the website (app/server_admin.py), same definitions.

-- Settings of each server, written by the website
CREATE TABLE IF NOT EXISTS server_levelup (
    server_id BIGINT PRIMARY KEY,
    enabled BOOLEAN NOT NULL DEFAULT FALSE,
    channel_id BIGINT,                              -- announcement channel (also for level-ups in voice)
    same_channel BOOLEAN NOT NULL DEFAULT FALSE,    -- announce where the member just wrote
    message TEXT,                                   -- {membre} {niveau} {serveur}; NULL: default text in the server's language
    mention BOOLEAN NOT NULL DEFAULT TRUE,
    min_level INTEGER NOT NULL DEFAULT 2,
    every INTEGER NOT NULL DEFAULT 1,               -- 1, 2, 5 or 10
    with_card BOOLEAN NOT NULL DEFAULT TRUE,
    updated_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT NOW(),
    updated_by BIGINT
);

-- Last level the bot saw for each member of each server (a level is announced once, never those reached before)
CREATE TABLE IF NOT EXISTS levelup_state (
    server_id BIGINT NOT NULL,
    user_id BIGINT NOT NULL,
    level INTEGER NOT NULL,
    announced_at TIMESTAMP WITHOUT TIME ZONE,
    PRIMARY KEY (server_id, user_id)
);
