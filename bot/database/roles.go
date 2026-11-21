package database

import (
	"context"
	"encoding/json"
	"time"
)

// Automatic roles (server management, "Roles" tab of the website). The rules are written by the website
// (server_roles, server_role_rules); the bot gives and removes the roles, and remembers the ones it gave itself
// (role_grants): a role given by hand is never removed.

// RoleCondition is one condition of a rule: metric "voice" (hours), "messages" or "level" (level on the server),
// scope "total" (since the start on this server) or "30d" (last 30 days; not for the level).
type RoleCondition struct {
	Metric string  `json:"metric"`
	Scope  string  `json:"scope"`
	Min    float64 `json:"min"`
}

// RoleRule gives one role when its conditions are met: all of them (Match "all") or at least one ("any").
type RoleRule struct {
	ID         int64
	RoleID     int64
	Match      string
	Conditions []RoleCondition
}

// RoleSettings is the configuration of one server; Rules are in the order of the page (easiest first).
type RoleSettings struct {
	ServerID    int64
	KeepHighest bool // tiers: only the role of the last rule met is kept
	RemoveUnmet bool // a role the bot gave is removed when its rule is no longer met
	UpdatedAt   time.Time
	Rules       []RoleRule
}

// MemberMetrics is the activity of a member on a server, as the rules read it.
type MemberMetrics struct {
	VoiceTotal  int64 // seconds, session in progress included
	Voice30d    int64
	MessagesAll int64
	Messages30d int64
}

// EnsureRoleTables creates the tables on startup when they are missing (same definitions as the website's).
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
	return nil
}

// LoadRoleSettings returns the servers where the automatic roles are turned on (bot present), with their rules.
func (db *DB) LoadRoleSettings(ctx context.Context) (map[int64]*RoleSettings, error) {
	rows, err := db.Pool.Query(ctx, `
		SELECT r.server_id, r.keep_highest, r.remove_unmet, r.updated_at
		FROM server_roles r LEFT JOIN guild_meta m ON m.server_id = r.server_id
		WHERE r.enabled AND COALESCE(m.bot_present, TRUE)`)
	if err != nil {
		return nil, err
	}
	out := make(map[int64]*RoleSettings)
	for rows.Next() {
		s := &RoleSettings{}
		if err := rows.Scan(&s.ServerID, &s.KeepHighest, &s.RemoveUnmet, &s.UpdatedAt); err != nil {
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

	rules, err := db.Pool.Query(ctx, `
		SELECT r.id, r.server_id, r.role_id, r.match, r.conditions FROM server_role_rules r
		JOIN server_roles s ON s.server_id = r.server_id AND s.enabled ORDER BY r.server_id, r.position, r.id`)
	if err != nil {
		return nil, err
	}
	defer rules.Close()
	for rules.Next() {
		var rule RoleRule
		var serverID int64
		var conditions string
		if err := rules.Scan(&rule.ID, &serverID, &rule.RoleID, &rule.Match, &conditions); err != nil {
			return nil, err
		}
		s, ok := out[serverID]
		if !ok {
			continue
		}
		if json.Unmarshal([]byte(conditions), &rule.Conditions) != nil || len(rule.Conditions) == 0 {
			continue // unreadable rule: ignored rather than giving a role on a wrong reading
		}
		s.Rules = append(s.Rules, rule)
	}
	return out, rules.Err()
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
