package database

import (
	"context"
	"time"

	"github.com/jackc/pgx/v5"
)

// Copy of each server as Discord sees it, kept up to date by the bot and read by the website (server management
// page, owner and member checks): owner, language, the bot's own permissions, text channels, roles and members.
// The website never needs the bot token to know them. Server settings themselves are written by the website.

// GuildMeta is one row of guild_meta.
type GuildMeta struct {
	ServerID           int64
	OwnerID            int64
	Locale             string
	BotPermissions     int64 // server-wide permissions of the bot (all of them when it is administrator)
	BotTopRolePosition int   // position of the bot's highest role: it can only give roles below it
	MemberCount        int
}

// GuildChannel is a text channel and what the bot may do in it.
type GuildChannel struct {
	ChannelID int64
	Name      string
	Kind      string // "text" or "announcement"
	Category  string
	Position  int
	CanView   bool
	CanSend   bool
	CanEmbed  bool
	CanAttach bool
}

// GuildRole is a role of the server; Assignable when the bot could give it, Dangerous when it carries
// moderation or administration rights (never given automatically).
type GuildRole struct {
	RoleID      int64
	Name        string
	Color       int
	Position    int
	Managed     bool
	Permissions int64
	Assignable  bool
	Dangerous   bool
}

// GuildMember is a person present on the server (bots are not stored).
type GuildMember struct {
	UserID      int64
	Username    string
	DisplayName string
	Avatar      string
	JoinedAt    *time.Time
}

// EnsureGuildStateTables creates the tables on startup when they are missing (safe to run every time).
func (db *DB) EnsureGuildStateTables(ctx context.Context) error {
	statements := []string{
		`CREATE TABLE IF NOT EXISTS guild_meta (
			server_id BIGINT PRIMARY KEY,
			owner_id BIGINT,
			locale VARCHAR(16),
			bot_permissions BIGINT NOT NULL DEFAULT 0,
			bot_top_role_position INTEGER NOT NULL DEFAULT 0,
			member_count INTEGER NOT NULL DEFAULT 0,
			bot_present BOOLEAN NOT NULL DEFAULT TRUE,
			synced_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT NOW(),
			members_synced_at TIMESTAMP WITHOUT TIME ZONE
		)`,
		`CREATE INDEX IF NOT EXISTS guild_meta_owner ON guild_meta (owner_id)`,
		`CREATE TABLE IF NOT EXISTS guild_channels (
			server_id BIGINT NOT NULL,
			channel_id BIGINT NOT NULL,
			name VARCHAR(100) NOT NULL,
			kind VARCHAR(16) NOT NULL,
			category VARCHAR(100),
			position INTEGER NOT NULL DEFAULT 0,
			can_view BOOLEAN NOT NULL DEFAULT FALSE,
			can_send BOOLEAN NOT NULL DEFAULT FALSE,
			can_embed BOOLEAN NOT NULL DEFAULT FALSE,
			can_attach BOOLEAN NOT NULL DEFAULT FALSE,
			PRIMARY KEY (server_id, channel_id)
		)`,
		`CREATE TABLE IF NOT EXISTS guild_roles (
			server_id BIGINT NOT NULL,
			role_id BIGINT NOT NULL,
			name VARCHAR(100) NOT NULL,
			color INTEGER NOT NULL DEFAULT 0,
			position INTEGER NOT NULL DEFAULT 0,
			managed BOOLEAN NOT NULL DEFAULT FALSE,
			permissions BIGINT NOT NULL DEFAULT 0,
			assignable BOOLEAN NOT NULL DEFAULT FALSE,
			dangerous BOOLEAN NOT NULL DEFAULT FALSE,
			PRIMARY KEY (server_id, role_id)
		)`,
		`CREATE TABLE IF NOT EXISTS guild_members (
			server_id BIGINT NOT NULL,
			user_id BIGINT NOT NULL,
			username VARCHAR(100),
			display_name VARCHAR(100),
			avatar TEXT,
			joined_at TIMESTAMP WITHOUT TIME ZONE,
			PRIMARY KEY (server_id, user_id)
		)`,
		`CREATE INDEX IF NOT EXISTS guild_members_user ON guild_members (user_id)`,
		// Journal of the server management features (also written by the website: settings changes)
		`CREATE TABLE IF NOT EXISTS server_feature_log (
			id BIGSERIAL PRIMARY KEY,
			server_id BIGINT NOT NULL,
			created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT NOW(),
			feature VARCHAR(16) NOT NULL,
			action VARCHAR(32) NOT NULL,
			actor_id BIGINT,
			target_id BIGINT,
			ok BOOLEAN NOT NULL DEFAULT TRUE,
			detail TEXT
		)`,
		`CREATE INDEX IF NOT EXISTS server_feature_log_server ON server_feature_log (server_id, created_at DESC)`,
		`CREATE INDEX IF NOT EXISTS server_feature_log_created ON server_feature_log (created_at)`,
	}
	for _, sql := range statements {
		if _, err := db.Pool.Exec(ctx, sql); err != nil {
			return err
		}
	}
	return nil
}

// SaveGuildState replaces the copy of one server (meta, channels, roles) in a single transaction.
func (db *DB) SaveGuildState(ctx context.Context, meta GuildMeta, channels []GuildChannel, roles []GuildRole) error {
	tx, err := db.Pool.Begin(ctx)
	if err != nil {
		return err
	}
	defer tx.Rollback(ctx)

	if _, err := tx.Exec(ctx, `
		INSERT INTO guild_meta (server_id, owner_id, locale, bot_permissions, bot_top_role_position, member_count, bot_present, synced_at)
		VALUES ($1, $2, $3, $4, $5, $6, TRUE, NOW())
		ON CONFLICT (server_id) DO UPDATE SET owner_id = EXCLUDED.owner_id, locale = EXCLUDED.locale,
			bot_permissions = EXCLUDED.bot_permissions, bot_top_role_position = EXCLUDED.bot_top_role_position,
			member_count = EXCLUDED.member_count, bot_present = TRUE, synced_at = NOW()`,
		meta.ServerID, meta.OwnerID, meta.Locale, meta.BotPermissions, meta.BotTopRolePosition, meta.MemberCount); err != nil {
		return err
	}

	if _, err := tx.Exec(ctx, `DELETE FROM guild_channels WHERE server_id = $1`, meta.ServerID); err != nil {
		return err
	}
	if len(channels) > 0 {
		rows := make([][]any, 0, len(channels))
		for _, c := range channels {
			rows = append(rows, []any{meta.ServerID, c.ChannelID, trim(c.Name, 100), c.Kind, trim(c.Category, 100), c.Position,
				c.CanView, c.CanSend, c.CanEmbed, c.CanAttach})
		}
		if _, err := tx.CopyFrom(ctx, pgx.Identifier{"guild_channels"},
			[]string{"server_id", "channel_id", "name", "kind", "category", "position", "can_view", "can_send", "can_embed", "can_attach"},
			pgx.CopyFromRows(rows)); err != nil {
			return err
		}
	}

	if _, err := tx.Exec(ctx, `DELETE FROM guild_roles WHERE server_id = $1`, meta.ServerID); err != nil {
		return err
	}
	if len(roles) > 0 {
		rows := make([][]any, 0, len(roles))
		for _, r := range roles {
			rows = append(rows, []any{meta.ServerID, r.RoleID, trim(r.Name, 100), r.Color, r.Position, r.Managed, r.Permissions, r.Assignable, r.Dangerous})
		}
		if _, err := tx.CopyFrom(ctx, pgx.Identifier{"guild_roles"},
			[]string{"server_id", "role_id", "name", "color", "position", "managed", "permissions", "assignable", "dangerous"},
			pgx.CopyFromRows(rows)); err != nil {
			return err
		}
	}
	return tx.Commit(ctx)
}

// ReplaceGuildMembers replaces the member list of one server (after the full list arrived from Discord).
func (db *DB) ReplaceGuildMembers(ctx context.Context, serverID int64, members []GuildMember) error {
	tx, err := db.Pool.Begin(ctx)
	if err != nil {
		return err
	}
	defer tx.Rollback(ctx)
	if _, err := tx.Exec(ctx, `DELETE FROM guild_members WHERE server_id = $1`, serverID); err != nil {
		return err
	}
	if len(members) > 0 {
		rows := make([][]any, 0, len(members))
		seen := make(map[int64]struct{}, len(members)) // one row per member, even if a list repeats someone
		for _, m := range members {
			if _, dup := seen[m.UserID]; dup {
				continue
			}
			seen[m.UserID] = struct{}{}
			rows = append(rows, []any{serverID, m.UserID, trim(m.Username, 100), trim(m.DisplayName, 100), m.Avatar, m.JoinedAt})
		}
		if _, err := tx.CopyFrom(ctx, pgx.Identifier{"guild_members"},
			[]string{"server_id", "user_id", "username", "display_name", "avatar", "joined_at"}, pgx.CopyFromRows(rows)); err != nil {
			return err
		}
	}
	if _, err := tx.Exec(ctx, `UPDATE guild_meta SET members_synced_at = NOW() WHERE server_id = $1`, serverID); err != nil {
		return err
	}
	return tx.Commit(ctx)
}

// UpsertGuildMember records one member who joined or changed (name, avatar).
func (db *DB) UpsertGuildMember(ctx context.Context, serverID int64, m GuildMember) error {
	_, err := db.Pool.Exec(ctx, `
		INSERT INTO guild_members (server_id, user_id, username, display_name, avatar, joined_at)
		VALUES ($1, $2, $3, $4, $5, $6)
		ON CONFLICT (server_id, user_id) DO UPDATE SET username = EXCLUDED.username, display_name = EXCLUDED.display_name,
			avatar = EXCLUDED.avatar, joined_at = COALESCE(EXCLUDED.joined_at, guild_members.joined_at)`,
		serverID, m.UserID, trim(m.Username, 100), trim(m.DisplayName, 100), m.Avatar, m.JoinedAt)
	return err
}

// DeleteGuildMember forgets a member who left the server (or was kicked or banned).
func (db *DB) DeleteGuildMember(ctx context.Context, serverID, userID int64) error {
	_, err := db.Pool.Exec(ctx, `DELETE FROM guild_members WHERE server_id = $1 AND user_id = $2`, serverID, userID)
	return err
}

// SetGuildBotPresence flags a server the bot left (its copy and its settings are kept: they come back with the bot).
func (db *DB) SetGuildBotPresence(ctx context.Context, serverID int64, present bool) error {
	_, err := db.Pool.Exec(ctx, `UPDATE guild_meta SET bot_present = $2 WHERE server_id = $1`, serverID, present)
	return err
}

// FeatureLog is one line of the server management journal.
type FeatureLog struct {
	ServerID int64
	Feature  string // "general", "levels", "reports", "roles"
	Action   string
	ActorID  int64 // member who caused it (0: none)
	TargetID int64 // member, channel or role concerned (0: none)
	OK       bool
	Detail   string
}

// LogFeature writes one line of the journal shown on the server management page and the admin page.
func (db *DB) LogFeature(ctx context.Context, e FeatureLog) error {
	_, err := db.Pool.Exec(ctx, `
		INSERT INTO server_feature_log (server_id, feature, action, actor_id, target_id, ok, detail)
		VALUES ($1, $2, $3, NULLIF($4, 0), NULLIF($5, 0), $6, NULLIF($7, ''))`,
		e.ServerID, e.Feature, e.Action, e.ActorID, e.TargetID, e.OK, trim(e.Detail, 500))
	return err
}

func trim(s string, max int) string {
	r := []rune(s)
	if len(r) > max {
		return string(r[:max])
	}
	return s
}
