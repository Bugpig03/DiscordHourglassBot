package database

import (
	"context"
	"encoding/json"
	"time"
)

// Automatic roles (server management, "Roles" tab of the website). The rules are written by the website
// (server_roles, server_role_ladders, server_role_tiers); the bot gives and removes the roles, and remembers the ones
// it gave itself (role_grants): a role given by hand is never removed.
//
// A rule is a progression of tiers (10 h -> Regular, 50 h -> Veteran, 100 h -> Legend): each tier gives one role
// when its conditions are met, and the rule either stacks the roles of every tier met or keeps the highest only.

// RoleCondition is one condition of a tier: metric "voice" (hours), "messages" or "level" (level on the server),
// scope "total" (since the start on this server) or "30d" (last 30 days; not for the level).
type RoleCondition struct {
	Metric string  `json:"metric"`
	Scope  string  `json:"scope"`
	Min    float64 `json:"min"`
}

// RoleRule is one tier: one role, given when its conditions are met, all of them (Match "all") or at least one ("any").
type RoleRule struct {
	ID         int64
	RoleID     int64
	Match      string
	Conditions []RoleCondition
}

// RoleLadder is one rule of the page: its tiers in order (easiest first) and how they combine.
type RoleLadder struct {
	ID          int64
	KeepHighest bool // only the role of the last tier met is kept (else the roles of every tier met)
	Tiers       []RoleRule
}

// RoleSettings is the configuration of one server; Ladders are in the order of the page.
type RoleSettings struct {
	ServerID    int64
	RemoveUnmet bool // a role the bot gave is removed when no tier giving it is met any more
	UpdatedAt   time.Time
	Ladders     []RoleLadder
}

// MemberMetrics is the activity of a member on a server, as the rules read it.
type MemberMetrics struct {
	VoiceTotal  int64 // seconds, session in progress included
	Voice30d    int64
	MessagesAll int64
	Messages30d int64
}

// EnsureRoleTables creates the tables on startup when they are missing (same definitions as the website's), and
// turns the rules of bot 3.11.0 (one role each, server_role_rules) into one-tier rules.
func (db *DB) EnsureRoleTables(ctx context.Context) error {
	statements := []string{
		`CREATE TABLE IF NOT EXISTS server_roles (
			server_id BIGINT PRIMARY KEY,
			enabled BOOLEAN NOT NULL DEFAULT FALSE,
			keep_highest BOOLEAN NOT NULL DEFAULT FALSE,
			remove_unmet BOOLEAN NOT NULL DEFAULT TRUE,
			updated_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT NOW(),
			updated_by BIGINT
		)`,
		`CREATE TABLE IF NOT EXISTS server_role_rules (
			id BIGSERIAL PRIMARY KEY,
			server_id BIGINT NOT NULL,
			position INTEGER NOT NULL DEFAULT 0,
			role_id BIGINT NOT NULL,
			match VARCHAR(3) NOT NULL DEFAULT 'all',
			conditions TEXT NOT NULL
		)`,
		`CREATE INDEX IF NOT EXISTS server_role_rules_server ON server_role_rules (server_id, position)`,
		`CREATE TABLE IF NOT EXISTS server_role_ladders (
			id BIGSERIAL PRIMARY KEY,
			server_id BIGINT NOT NULL,
			position INTEGER NOT NULL DEFAULT 0,
			keep_highest BOOLEAN NOT NULL DEFAULT TRUE
		)`,
		`CREATE INDEX IF NOT EXISTS server_role_ladders_server ON server_role_ladders (server_id, position)`,
		`CREATE TABLE IF NOT EXISTS server_role_tiers (
			id BIGSERIAL PRIMARY KEY,
			ladder_id BIGINT NOT NULL,
			server_id BIGINT NOT NULL,
			position INTEGER NOT NULL DEFAULT 0,
			role_id BIGINT NOT NULL,
			match VARCHAR(3) NOT NULL DEFAULT 'all',
			conditions TEXT NOT NULL
		)`,
		`CREATE INDEX IF NOT EXISTS server_role_tiers_server ON server_role_tiers (server_id, ladder_id, position)`,
		`CREATE TABLE IF NOT EXISTS role_grants (
			server_id BIGINT NOT NULL,
			user_id BIGINT NOT NULL,
			role_id BIGINT NOT NULL,
			granted_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT NOW(),
			PRIMARY KEY (server_id, user_id, role_id)
		)`,
	}
	for _, sql := range statements {
		if _, err := db.Pool.Exec(ctx, sql); err != nil {
			return err
		}
	}
	return db.migrateRoleRules(ctx)
}

// migrateRoleRules: each server still on the 3.11.0 rules gets one rule holding them as tiers, with the server's
// former "tiers" choice (same behaviour as before), then the old rows are removed.
func (db *DB) migrateRoleRules(ctx context.Context) error {
	tx, err := db.Pool.Begin(ctx)
	if err != nil {
		return err
	}
	defer tx.Rollback(ctx)
	if _, err := tx.Exec(ctx, `
		WITH todo AS (
			SELECT DISTINCT r.server_id FROM server_role_rules r
			WHERE NOT EXISTS (SELECT 1 FROM server_role_ladders l WHERE l.server_id = r.server_id)),
		ladder AS (
			INSERT INTO server_role_ladders (server_id, position, keep_highest)
			SELECT t.server_id, 0, COALESCE((SELECT s.keep_highest FROM server_roles s WHERE s.server_id = t.server_id), FALSE)
			FROM todo t RETURNING id, server_id)
		INSERT INTO server_role_tiers (ladder_id, server_id, position, role_id, match, conditions)
		SELECT ladder.id, r.server_id, r.position, r.role_id, r.match, r.conditions
		FROM server_role_rules r JOIN ladder ON ladder.server_id = r.server_id`); err != nil {
		return err
	}
	if _, err := tx.Exec(ctx, `DELETE FROM server_role_rules`); err != nil {
		return err
	}
	return tx.Commit(ctx)
}

// LoadRoleSettings returns the servers where the automatic roles are turned on (bot present), with their rules.
func (db *DB) LoadRoleSettings(ctx context.Context) (map[int64]*RoleSettings, error) {
	rows, err := db.Pool.Query(ctx, `
		SELECT r.server_id, r.remove_unmet, r.updated_at
		FROM server_roles r LEFT JOIN guild_meta m ON m.server_id = r.server_id
		WHERE r.enabled AND COALESCE(m.bot_present, TRUE)`)
	if err != nil {
		return nil, err
	}
	out := make(map[int64]*RoleSettings)
	for rows.Next() {
		s := &RoleSettings{}
		if err := rows.Scan(&s.ServerID, &s.RemoveUnmet, &s.UpdatedAt); err != nil {
			rows.Close()
			return nil, err
		}
		out[s.ServerID] = s
	}
	rows.Close()
	if err := rows.Err(); err != nil {
		return nil, err
	}
	if len(out) == 0 {
		return out, nil
	}

	tiers, err := db.Pool.Query(ctx, `
		SELECT l.server_id, l.id, l.keep_highest, t.id, t.role_id, t.match, t.conditions
		FROM server_role_ladders l JOIN server_roles s ON s.server_id = l.server_id AND s.enabled
		JOIN server_role_tiers t ON t.ladder_id = l.id
		ORDER BY l.server_id, l.position, l.id, t.position, t.id`)
	if err != nil {
		return nil, err
	}
	defer tiers.Close()
	for tiers.Next() {
		var serverID, ladderID int64
		var keep bool
		var tier RoleRule
		var conditions string
		if err := tiers.Scan(&serverID, &ladderID, &keep, &tier.ID, &tier.RoleID, &tier.Match, &conditions); err != nil {
			return nil, err
		}
		s, ok := out[serverID]
		if !ok {
			continue
		}
		// Unreadable tier: ignored rather than giving a role on a wrong reading. A readable empty list ("[]") is a
		// tier without condition, given to every member.
		if json.Unmarshal([]byte(conditions), &tier.Conditions) != nil || tier.Conditions == nil {
			continue
		}
		if n := len(s.Ladders); n == 0 || s.Ladders[n-1].ID != ladderID {
			s.Ladders = append(s.Ladders, RoleLadder{ID: ladderID, KeepHighest: keep})
		}
		last := &s.Ladders[len(s.Ladders)-1]
		last.Tiers = append(last.Tiers, tier)
	}
	return out, tiers.Err()
}

// ServerMemberMetrics returns the activity of the members of a server (bot copy of the member list), or of one
// member only when userID is not 0.
func (db *DB) ServerMemberMetrics(ctx context.Context, serverID, userID int64) (map[int64]MemberMetrics, error) {
	rows, err := db.Pool.Query(ctx, `
		WITH m AS (SELECT user_id FROM guild_members WHERE server_id = $1 AND ($2::BIGINT = 0 OR user_id = $2)),
		live AS (
			SELECT user_id, SUM(GREATEST(0, EXTRACT(EPOCH FROM (NOW() - joined_at))))::BIGINT AS sec FROM voice_sessions
			WHERE server_id = $1 AND left_at IS NULL AND NOT COALESCE(is_legacy, FALSE) AND ($2::BIGINT = 0 OR user_id = $2) GROUP BY user_id),
		v30 AS (
			SELECT user_id, SUM(COALESCE(duration_seconds, 0))::BIGINT AS sec FROM voice_sessions
			WHERE server_id = $1 AND left_at IS NOT NULL AND joined_at >= NOW() - INTERVAL '30 days' AND ($2::BIGINT = 0 OR user_id = $2) GROUP BY user_id),
		m30 AS (
			SELECT user_id, SUM(COALESCE(count, 1))::BIGINT AS n FROM message_events
			WHERE server_id = $1 AND created_at >= NOW() - INTERVAL '30 days' AND ($2::BIGINT = 0 OR user_id = $2) GROUP BY user_id)
		SELECT m.user_id, COALESCE(s.seconds, 0)::BIGINT + COALESCE(live.sec, 0), COALESCE(v30.sec, 0) + COALESCE(live.sec, 0),
			COALESCE(s.messages, 0)::BIGINT, COALESCE(m30.n, 0)
		FROM m LEFT JOIN stats s ON s.user_id = m.user_id AND s.server_id = $1
		LEFT JOIN live ON live.user_id = m.user_id LEFT JOIN v30 ON v30.user_id = m.user_id LEFT JOIN m30 ON m30.user_id = m.user_id`,
		serverID, userID)
	if err != nil {
		return nil, err
	}
	defer rows.Close()
	out := make(map[int64]MemberMetrics)
	for rows.Next() {
		var id int64
		var mm MemberMetrics
		if err := rows.Scan(&id, &mm.VoiceTotal, &mm.Voice30d, &mm.MessagesAll, &mm.Messages30d); err != nil {
			return nil, err
		}
		out[id] = mm
	}
	return out, rows.Err()
}

// RoleGrants returns the roles the bot gave on a server: {user: {role: true}} (one member only when userID is not 0).
func (db *DB) RoleGrants(ctx context.Context, serverID, userID int64) (map[int64]map[int64]bool, error) {
	rows, err := db.Pool.Query(ctx, `SELECT user_id, role_id FROM role_grants WHERE server_id = $1 AND ($2::BIGINT = 0 OR user_id = $2)`,
		serverID, userID)
	if err != nil {
		return nil, err
	}
	defer rows.Close()
	out := make(map[int64]map[int64]bool)
	for rows.Next() {
		var user, role int64
		if err := rows.Scan(&user, &role); err != nil {
			return nil, err
		}
		if out[user] == nil {
			out[user] = map[int64]bool{}
		}
		out[user][role] = true
	}
	return out, rows.Err()
}

// SetRoleGrant records (granted) or forgets a role the bot gave.
func (db *DB) SetRoleGrant(ctx context.Context, serverID, userID, roleID int64, granted bool) error {
	if granted {
		_, err := db.Pool.Exec(ctx, `INSERT INTO role_grants (server_id, user_id, role_id) VALUES ($1, $2, $3) ON CONFLICT DO NOTHING`,
			serverID, userID, roleID)
		return err
	}
	_, err := db.Pool.Exec(ctx, `DELETE FROM role_grants WHERE server_id = $1 AND user_id = $2 AND role_id = $3`, serverID, userID, roleID)
	return err
}
