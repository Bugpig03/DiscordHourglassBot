-- bot v3.7.0: copy of the bot's log lines (also created automatically by the bot at startup).
-- Written by the bot in batches every 2 seconds, trimmed to the 500 latest lines every 10 minutes.
-- Read by the website admin page (section "Logs du bot", web v3.33.0), which shows the last 200.
CREATE TABLE IF NOT EXISTS bot_logs (
    id BIGSERIAL PRIMARY KEY,
    created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT NOW(), -- when the line was logged (UTC)
    line TEXT NOT NULL                                              -- the line, without the date prefix, cut at 2000 characters
);
