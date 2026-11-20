-- bot v3.10.0 + web v3.45.0: automatic reports (server management > Reports). Created automatically at startup by both
-- the bot (database/reports.go) and the website (app/server_admin.py), same definitions.

-- Settings of each report of each server, written by the website
CREATE TABLE IF NOT EXISTS server_reports (
    server_id BIGINT NOT NULL,
    kind VARCHAR(8) NOT NULL,                       -- daily, weekly, monthly
    enabled BOOLEAN NOT NULL DEFAULT FALSE,
    channel_id BIGINT,
    hour SMALLINT NOT NULL DEFAULT 20,              -- local hour of the server (server_settings.timezone)
    weekday SMALLINT NOT NULL DEFAULT 6,            -- weekly: 0 = Monday ... 6 = Sunday
    mention_role_id BIGINT,
    updated_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT NOW(),
    updated_by BIGINT,
    PRIMARY KEY (server_id, kind)
);

-- Reports the bot sent: booked before sending, so a report is never posted twice (even after a restart)
CREATE TABLE IF NOT EXISTS report_runs (
    server_id BIGINT NOT NULL,
    kind VARCHAR(8) NOT NULL,
    period_start DATE NOT NULL,                     -- first local day of the period covered
    sent_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT NOW(),
    ok BOOLEAN,
    detail TEXT,
    PRIMARY KEY (server_id, kind, period_start)
);

-- Tests asked from the website ("Save and send a test"), handled by the bot within a minute
CREATE TABLE IF NOT EXISTS report_requests (
    id BIGSERIAL PRIMARY KEY,
    server_id BIGINT NOT NULL,
    kind VARCHAR(8) NOT NULL,
    requested_by BIGINT,
    created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT NOW(),
    done_at TIMESTAMP WITHOUT TIME ZONE,
    ok BOOLEAN,
    detail TEXT
);
CREATE INDEX IF NOT EXISTS report_requests_pending ON report_requests (created_at) WHERE done_at IS NULL;

-- The bot also creates server_settings when the website has not yet (same definition as the web v3.42.0 migration)
