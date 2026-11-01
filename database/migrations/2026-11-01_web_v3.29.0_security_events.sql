-- web v3.29.0: security journal of the admin page (also created automatically by the site at startup).
-- Shortened IP only (IPv4 a.b.c.x, IPv6 /48); rows are deleted by the site after 90 days.
CREATE TABLE IF NOT EXISTS web_security_events (
    id BIGSERIAL PRIMARY KEY,
    at TIMESTAMP WITHOUT TIME ZONE NOT NULL,
    kind VARCHAR(24) NOT NULL,
    ip VARCHAR(48),
    path VARCHAR(160),
    user_id BIGINT,
    detail VARCHAR(200),
    hits INTEGER NOT NULL DEFAULT 1
);
CREATE INDEX IF NOT EXISTS web_security_events_at ON web_security_events (at);
CREATE INDEX IF NOT EXISTS web_security_events_kind_at ON web_security_events (kind, at);
