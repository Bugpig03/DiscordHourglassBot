package database

import (
	"context"
	"time"
)

// Automatic reports (server management, "Reports" tab of the website): daily, weekly and monthly summaries posted by
// the bot in a channel. The website writes the settings (server_reports) and test requests (report_requests); the bot
// books each report it sends in report_runs, so a report is never posted twice, even after a restart.

// ReportSettings is one report of one server.
type ReportSettings struct {
	ServerID    int64
	Kind        string // daily, weekly, monthly
	ChannelID   int64
	Hour        int // local hour of the server (0-23)
	Weekday     int // weekly: 0 = Monday … 6 = Sunday
	MentionRole int64
	Timezone    string
	Locale      string
	Since       time.Time // last change: a report due before it is not sent (no surprise right after turning it on)
}

// ReportRequest is a test asked from the website ("Send a test now").
type ReportRequest struct {
	ID          int64
	ServerID    int64
	Kind        string
	RequestedBy int64
}

// EnsureReportTables creates the tables on startup when they are missing (same definitions as the website's).
func (db *DB) EnsureReportTables(ctx context.Context) error {
	statements := []string{
		`CREATE TABLE IF NOT EXISTS server_settings (
			server_id BIGINT PRIMARY KEY,
			timezone VARCHAR(64) NOT NULL DEFAULT 'Europe/Paris',
			private BOOLEAN NOT NULL DEFAULT FALSE,
			updated_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT NOW(),
			updated_by BIGINT
		)`,
		`CREATE TABLE IF NOT EXISTS server_reports (
			server_id BIGINT NOT NULL,
			kind VARCHAR(8) NOT NULL,
			enabled BOOLEAN NOT NULL DEFAULT FALSE,
			channel_id BIGINT,
			hour SMALLINT NOT NULL DEFAULT 20,
			weekday SMALLINT NOT NULL DEFAULT 6,
			mention_role_id BIGINT,
			updated_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT NOW(),
			updated_by BIGINT,
			PRIMARY KEY (server_id, kind)
		)`,
		`CREATE TABLE IF NOT EXISTS report_runs (
			server_id BIGINT NOT NULL,
			kind VARCHAR(8) NOT NULL,
			period_start DATE NOT NULL,
			sent_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT NOW(),
			ok BOOLEAN,
			detail TEXT,
			PRIMARY KEY (server_id, kind, period_start)
		)`,
		`CREATE TABLE IF NOT EXISTS report_requests (
			id BIGSERIAL PRIMARY KEY,
			server_id BIGINT NOT NULL,
			kind VARCHAR(8) NOT NULL,
			requested_by BIGINT,
			created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT NOW(),
			done_at TIMESTAMP WITHOUT TIME ZONE,
			ok BOOLEAN,
			detail TEXT
		)`,
		`CREATE INDEX IF NOT EXISTS report_requests_pending ON report_requests (created_at) WHERE done_at IS NULL`,
	}
	for _, sql := range statements {
		if _, err := db.Pool.Exec(ctx, sql); err != nil {
			return err
		}
	}
	return nil
}

// LoadReportSettings returns every report turned on, on the servers where the bot is.
func (db *DB) LoadReportSettings(ctx context.Context) ([]ReportSettings, error) {
	rows, err := db.Pool.Query(ctx, `
		SELECT r.server_id, r.kind, COALESCE(r.channel_id, 0), r.hour, r.weekday, COALESCE(r.mention_role_id, 0),
			COALESCE(s.timezone, 'Europe/Paris'), COALESCE(m.locale, ''), r.updated_at
		FROM server_reports r
		LEFT JOIN server_settings s ON s.server_id = r.server_id
		LEFT JOIN guild_meta m ON m.server_id = r.server_id
		WHERE r.enabled AND COALESCE(m.bot_present, TRUE)`)
	if err != nil {
		return nil, err
	}
	defer rows.Close()
	var out []ReportSettings
	for rows.Next() {
		var r ReportSettings
		if err := rows.Scan(&r.ServerID, &r.Kind, &r.ChannelID, &r.Hour, &r.Weekday, &r.MentionRole, &r.Timezone, &r.Locale, &r.Since); err != nil {
			return nil, err
		}
		out = append(out, r)
	}
	return out, rows.Err()
}

// ReportSettingsFor returns one report's settings, turned on or not (tests from the website).
func (db *DB) ReportSettingsFor(ctx context.Context, serverID int64, kind string) (ReportSettings, error) {
	var r ReportSettings
	err := db.Pool.QueryRow(ctx, `
		SELECT $1::BIGINT, $2::VARCHAR, COALESCE(r.channel_id, 0), COALESCE(r.hour, 20), COALESCE(r.weekday, 6), COALESCE(r.mention_role_id, 0),
			COALESCE(s.timezone, 'Europe/Paris'), COALESCE(m.locale, ''), COALESCE(r.updated_at, NOW())
		FROM (SELECT 1) one
		LEFT JOIN server_reports r ON r.server_id = $1 AND r.kind = $2
		LEFT JOIN server_settings s ON s.server_id = $1
		LEFT JOIN guild_meta m ON m.server_id = $1`, serverID, kind).
		Scan(&r.ServerID, &r.Kind, &r.ChannelID, &r.Hour, &r.Weekday, &r.MentionRole, &r.Timezone, &r.Locale, &r.Since)
	return r, err
}

// ReserveReportRun books a report before sending it: false when it was already sent (or is being sent).
func (db *DB) ReserveReportRun(ctx context.Context, serverID int64, kind string, period time.Time) (bool, error) {
	tag, err := db.Pool.Exec(ctx, `
		INSERT INTO report_runs (server_id, kind, period_start) VALUES ($1, $2, $3)
		ON CONFLICT (server_id, kind, period_start) DO NOTHING`, serverID, kind, period.Format("2006-01-02"))
	if err != nil {
		return false, err
	}
	return tag.RowsAffected() == 1, nil
}

// FinishReportRun records how the sending went.
func (db *DB) FinishReportRun(ctx context.Context, serverID int64, kind string, period time.Time, ok bool, detail string) error {
	_, err := db.Pool.Exec(ctx, `UPDATE report_runs SET ok = $4, detail = NULLIF($5, '') WHERE server_id = $1 AND kind = $2 AND period_start = $3`,
		serverID, kind, period.Format("2006-01-02"), ok, trim(detail, 300))
	return err
}

// PendingReportRequests returns the tests asked in the last hour and not handled yet.
func (db *DB) PendingReportRequests(ctx context.Context) ([]ReportRequest, error) {
	rows, err := db.Pool.Query(ctx, `
		SELECT id, server_id, kind, COALESCE(requested_by, 0) FROM report_requests
		WHERE done_at IS NULL AND created_at > NOW() - INTERVAL '1 hour' ORDER BY created_at LIMIT 20`)
	if err != nil {
		return nil, err
	}
	defer rows.Close()
	var out []ReportRequest
	for rows.Next() {
		var r ReportRequest
		if err := rows.Scan(&r.ID, &r.ServerID, &r.Kind, &r.RequestedBy); err != nil {
			return nil, err
		}
		out = append(out, r)
	}
	return out, rows.Err()
}

// FinishReportRequest marks a test as handled.
func (db *DB) FinishReportRequest(ctx context.Context, id int64, ok bool, detail string) error {
	_, err := db.Pool.Exec(ctx, `UPDATE report_requests SET done_at = NOW(), ok = $2, detail = NULLIF($3, '') WHERE id = $1`, id, ok, trim(detail, 300))
	return err
}
