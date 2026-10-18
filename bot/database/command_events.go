package database

import (
	"context"
	"time"
)

// Slash command usage shown on the website admin page. No member identifier is stored:
// only the command, the server (NULL in DMs), the choice options (type/period/scope),
// whether it completed without panicking and how long it took.

const createCommandEventsTable = `
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
`

// EnsureCommandEventsTable creates the table when the migration was not applied (IF NOT EXISTS, harmless).
func (db *DB) EnsureCommandEventsTable(ctx context.Context) error {
	_, err := db.Pool.Exec(ctx, createCommandEventsTable)
	return err
}

// RecordCommand stores one slash command execution.
func (db *DB) RecordCommand(ctx context.Context, command string, serverID *int64, options string, success bool, duration time.Duration) error {
	if len(options) > 120 {
		options = options[:120]
	}
	_, err := db.Pool.Exec(ctx,
		`INSERT INTO bot_command_events (command, server_id, options, success, duration_ms, created_at)
		 VALUES ($1, $2, $3, $4, $5, NOW())`,
		command, serverID, options, success, int(duration.Milliseconds()))
	return err
}

// CleanOldCommandEvents removes command events older than 90 days.
func (db *DB) CleanOldCommandEvents(ctx context.Context) error {
	_, err := db.Pool.Exec(ctx, `DELETE FROM bot_command_events WHERE created_at < NOW() - INTERVAL '90 days'`)
	return err
}
