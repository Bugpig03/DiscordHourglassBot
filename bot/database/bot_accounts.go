package database

import (
	"context"
)

// EnsureUsersBotColumn adds users.is_bot when the migration was not applied (safe to run every time):
// the website shows a "BOT" tag on these accounts and hides them from its member rankings by default.
func (db *DB) EnsureUsersBotColumn(ctx context.Context) error {
	_, err := db.Pool.Exec(ctx, `ALTER TABLE users ADD COLUMN IF NOT EXISTS is_bot BOOLEAN NOT NULL DEFAULT FALSE`)
	db.hasBotColumn = err == nil
	return err
}

// MarkBots flags the given accounts as bots or apps (from the member lists of the servers, every 15 min),
// so the bots already recorded before is_bot existed are flagged without waiting for their next activity.
// Only rows that are not flagged yet are written.
func (db *DB) MarkBots(ctx context.Context, userIDs []int64) error {
	if len(userIDs) == 0 || !db.hasBotColumn {
		return nil
	}
	_, err := db.Pool.Exec(ctx, `UPDATE users SET is_bot = TRUE WHERE user_id = ANY($1) AND NOT is_bot`, userIDs)
	return err
}
