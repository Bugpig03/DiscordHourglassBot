package database

import (
	"context"
)

// MemberSnapshot counts the people present on the servers of the bot at one moment (from the member
// lists Discord sends with the guild members intent), each person counted once whatever their number
// of servers. Bots are excluded. Shown on the website admin page only.
type MemberSnapshot struct {
	UniqueMembers int // distinct members across every server
	UniqueOnline  int // of which online, idle or do not disturb
	Memberships   int // member x server pairs (a member on 3 servers counts 3)
	Servers       int // servers whose member list was available
	KnownMembers  int // of the unique members, those with recorded activity (a row in users)
}

// EnsureMemberSnapshotsTable creates the table on startup when it is missing (safe to run every time).
func (db *DB) EnsureMemberSnapshotsTable(ctx context.Context) error {
	_, err := db.Pool.Exec(ctx, `
		CREATE TABLE IF NOT EXISTS bot_member_snapshots (
			recorded_at TIMESTAMP WITHOUT TIME ZONE PRIMARY KEY DEFAULT NOW(),
			unique_members INTEGER NOT NULL,
			unique_online INTEGER NOT NULL,
			memberships INTEGER NOT NULL,
			servers INTEGER NOT NULL,
			known_members INTEGER NOT NULL
		)`)
	return err
}

// KnownUserIDs returns the members with recorded activity: the bot only adds a user after a message
// or a voice session, so the others are present on a server but never active.
func (db *DB) KnownUserIDs(ctx context.Context) (map[int64]struct{}, error) {
	rows, err := db.Pool.Query(ctx, `SELECT user_id FROM users`)
	if err != nil {
		return nil, err
	}
	defer rows.Close()
	known := make(map[int64]struct{})
	for rows.Next() {
		var id int64
		if rows.Scan(&id) == nil {
			known[id] = struct{}{}
		}
	}
	return known, rows.Err()
}

// RecordMemberSnapshot stores one snapshot and removes those older than 90 days.
func (db *DB) RecordMemberSnapshot(ctx context.Context, s MemberSnapshot) error {
	_, err := db.Pool.Exec(ctx, `
		INSERT INTO bot_member_snapshots (unique_members, unique_online, memberships, servers, known_members)
		VALUES ($1, $2, $3, $4, $5)
		ON CONFLICT (recorded_at) DO NOTHING`,
		s.UniqueMembers, s.UniqueOnline, s.Memberships, s.Servers, s.KnownMembers)
	if err != nil {
		return err
	}
	_, err = db.Pool.Exec(ctx, `DELETE FROM bot_member_snapshots WHERE recorded_at < NOW() - INTERVAL '90 days'`)
	return err
}
