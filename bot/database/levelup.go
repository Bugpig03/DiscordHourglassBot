package database

import (
	"context"
	"errors"

	"github.com/jackc/pgx/v5"
)

// Level-up announcements (server management, "Levels" tab of the website). The settings are written by the website
// (server_levelup); the bot keeps the last level it saw for each member of each server (levelup_state), so it only
// announces a level once, and never the levels reached before the feature was turned on.

// LevelupSettings is the configuration of one server.
type LevelupSettings struct {
	ServerID    int64
	ChannelID   int64  // announcement channel (also used for voice level-ups when SameChannel is set)
	SameChannel bool   // announce in the channel where the member just wrote
	Message     string // template with {membre}, {niveau}, {serveur}; empty: default text in the server's language
	Mention     bool
	MinLevel    int
	Every       int // announce every N levels (1: each one)
	WithCard    bool
	Locale      string // language of the server (guild_meta)
}

// EnsureLevelupTables creates the tables on startup when they are missing (same definitions as the website's).
func (db *DB) EnsureLevelupTables(ctx context.Context) error {
	statements := []string{
		`CREATE TABLE IF NOT EXISTS server_levelup (
			server_id BIGINT PRIMARY KEY,
			enabled BOOLEAN NOT NULL DEFAULT FALSE,
			channel_id BIGINT,
			same_channel BOOLEAN NOT NULL DEFAULT FALSE,
			message TEXT,
			mention BOOLEAN NOT NULL DEFAULT TRUE,
			min_level INTEGER NOT NULL DEFAULT 2,
			every INTEGER NOT NULL DEFAULT 1,
			with_card BOOLEAN NOT NULL DEFAULT TRUE,
			updated_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT NOW(),
			updated_by BIGINT
		)`,
		`CREATE TABLE IF NOT EXISTS levelup_state (
			server_id BIGINT NOT NULL,
			user_id BIGINT NOT NULL,
			level INTEGER NOT NULL,
			announced_at TIMESTAMP WITHOUT TIME ZONE,
			PRIMARY KEY (server_id, user_id)
		)`,
	}
	for _, sql := range statements {
		if _, err := db.Pool.Exec(ctx, sql); err != nil {
			return err
		}
	}
	return nil
}

// LoadLevelupSettings returns the servers where the announcements are turned on (bot present).
func (db *DB) LoadLevelupSettings(ctx context.Context) (map[int64]LevelupSettings, error) {
	rows, err := db.Pool.Query(ctx, `
		SELECT l.server_id, COALESCE(l.channel_id, 0), l.same_channel, COALESCE(l.message, ''), l.mention, l.min_level, l.every,
			l.with_card, COALESCE(m.locale, '')
		FROM server_levelup l LEFT JOIN guild_meta m ON m.server_id = l.server_id
		WHERE l.enabled AND COALESCE(m.bot_present, TRUE)`)
	if err != nil {
		return nil, err
	}
	defer rows.Close()
	out := make(map[int64]LevelupSettings)
	for rows.Next() {
		var s LevelupSettings
		if err := rows.Scan(&s.ServerID, &s.ChannelID, &s.SameChannel, &s.Message, &s.Mention, &s.MinLevel, &s.Every, &s.WithCard, &s.Locale); err != nil {
			return nil, err
		}
		out[s.ServerID] = s
	}
	return out, rows.Err()
}

// MemberServerActivity returns the voice seconds (session in progress included) and messages of a member on a server.
func (db *DB) MemberServerActivity(ctx context.Context, userID, serverID int64) (seconds int64, messages int64, err error) {
	err = db.Pool.QueryRow(ctx, `
		SELECT COALESCE((SELECT seconds FROM stats WHERE user_id = $1 AND server_id = $2), 0)
			+ COALESCE((SELECT SUM(GREATEST(0, EXTRACT(EPOCH FROM (NOW() - joined_at))))::BIGINT FROM voice_sessions
				WHERE user_id = $1 AND server_id = $2 AND left_at IS NULL AND NOT COALESCE(is_legacy, FALSE)), 0),
			COALESCE((SELECT messages FROM stats WHERE user_id = $1 AND server_id = $2), 0)`,
		userID, serverID).Scan(&seconds, &messages)
	return
}

// LevelupState returns the last level seen for a member on a server (found=false the first time).
func (db *DB) LevelupState(ctx context.Context, serverID, userID int64) (level int, found bool, err error) {
	err = db.Pool.QueryRow(ctx, `SELECT level FROM levelup_state WHERE server_id = $1 AND user_id = $2`, serverID, userID).Scan(&level)
	if errors.Is(err, pgx.ErrNoRows) {
		return 0, false, nil
	}
	return level, err == nil, err
}

// SetLevelupState records the level now reached (announced: an announcement was sent for it).
func (db *DB) SetLevelupState(ctx context.Context, serverID, userID int64, level int, announced bool) error {
	_, err := db.Pool.Exec(ctx, `
		INSERT INTO levelup_state (server_id, user_id, level, announced_at)
		VALUES ($1, $2, $3, CASE WHEN $4 THEN NOW() END)
		ON CONFLICT (server_id, user_id) DO UPDATE SET level = GREATEST(levelup_state.level, EXCLUDED.level),
			announced_at = COALESCE(EXCLUDED.announced_at, levelup_state.announced_at)`,
		serverID, userID, level, announced)
	return err
}
