package database

import (
	"context"
	"errors"
	"time"

	"github.com/jackc/pgx/v5"
)

// Patch notes on the official Discord server (website admin page > Patch notes). The website and the bot each write
// the entries of their own CHANGELOG at startup; the bot posts the new ones in the chosen channel.

// Patchnote is one version of the website ("web") or of the bot ("bot") and its CHANGELOG text.
type Patchnote struct {
	ID        int64
	Component string
	Version   string
	Title     string
	Released  string
	Body      string
	TitleEN   string // English entry (CHANGELOG.en.md); empty: the French text only is posted
	BodyEN    string
	Requested bool // asked from the admin page ("post the latest version now")
}

// PatchnoteSettings is the single row of patchnote_settings.
type PatchnoteSettings struct {
	Enabled     bool
	ServerID    int64
	ChannelID   int64
	Scope       string // "both", "web" or "bot"
	MentionRole int64
}

// registeredEntries: newest CHANGELOG entries written at startup (a version skipped by a fast deploy is caught)
const registeredEntries = 40

// EnsurePatchnoteTables creates the tables on startup when they are missing (same definitions as the website's).
func (db *DB) EnsurePatchnoteTables(ctx context.Context) error {
	statements := []string{
		`CREATE TABLE IF NOT EXISTS patchnote_settings (
			id SMALLINT PRIMARY KEY DEFAULT 1,
			enabled BOOLEAN NOT NULL DEFAULT FALSE,
			server_id BIGINT,
			channel_id BIGINT,
			scope VARCHAR(8) NOT NULL DEFAULT 'both',
			mention_role_id BIGINT,
			since TIMESTAMP WITHOUT TIME ZONE,
			updated_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT NOW(),
			updated_by BIGINT
		)`,
		`CREATE TABLE IF NOT EXISTS patchnotes (
			id BIGSERIAL PRIMARY KEY,
			component VARCHAR(8) NOT NULL,
			version VARCHAR(32) NOT NULL,
			title TEXT NOT NULL DEFAULT '',
			released VARCHAR(10),
			body TEXT NOT NULL,
			created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT NOW(),
			requested_at TIMESTAMP WITHOUT TIME ZONE,
			posted_at TIMESTAMP WITHOUT TIME ZONE,
			ok BOOLEAN,
			detail TEXT,
			baseline BOOLEAN NOT NULL DEFAULT FALSE,
			title_en TEXT NOT NULL DEFAULT '',
			body_en TEXT NOT NULL DEFAULT '',
			UNIQUE (component, version)
		)`,
	}
	for _, sql := range statements {
		if _, err := db.Pool.Exec(ctx, sql); err != nil {
			return err
		}
	}
	return nil
}

// RegisterPatchnotes writes the entries (given newest first) oldest first, so the ids follow the versions. An entry
// not posted yet takes the latest text of its CHANGELOG; a posted one is never touched.
//
// The very first time (no entry of this component yet), every entry is a "baseline": already known, never posted,
// so turning the patch notes on never floods the channel with the whole history. Locked per component (same lock
// as the website), so nobody ever sees a half-written first batch.
func (db *DB) RegisterPatchnotes(ctx context.Context, component string, entries []Patchnote) error {
	if len(entries) > registeredEntries {
		entries = entries[:registeredEntries]
	}
	tx, err := db.Pool.Begin(ctx)
	if err != nil {
		return err
	}
	defer tx.Rollback(ctx)
	if _, err := tx.Exec(ctx, `SELECT pg_advisory_xact_lock(hashtext($1))`, "patchnotes:"+component); err != nil {
		return err
	}
	var exists bool
	if err := tx.QueryRow(ctx, `SELECT EXISTS (SELECT 1 FROM patchnotes WHERE component = $1)`, component).Scan(&exists); err != nil {
		return err
	}
	for i := len(entries) - 1; i >= 0; i-- {
		e := entries[i]
		if _, err := tx.Exec(ctx, `
			INSERT INTO patchnotes (component, version, title, released, body, title_en, body_en, baseline)
			VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
			ON CONFLICT (component, version) DO UPDATE SET title = EXCLUDED.title, released = EXCLUDED.released,
				body = EXCLUDED.body, title_en = EXCLUDED.title_en, body_en = EXCLUDED.body_en WHERE patchnotes.posted_at IS NULL`,
			component, trim(e.Version, 32), e.Title, e.Released, e.Body, e.TitleEN, e.BodyEN, !exists); err != nil {
			return err
		}
	}
	return tx.Commit(ctx)
}

// LoadPatchnoteSettings returns the settings (found=false before the admin page saved any).
func (db *DB) LoadPatchnoteSettings(ctx context.Context) (s PatchnoteSettings, found bool, err error) {
	err = db.Pool.QueryRow(ctx, `
		SELECT enabled, COALESCE(server_id, 0), COALESCE(channel_id, 0), scope, COALESCE(mention_role_id, 0)
		FROM patchnote_settings WHERE id = 1`).Scan(&s.Enabled, &s.ServerID, &s.ChannelID, &s.Scope, &s.MentionRole)
	if errors.Is(err, pgx.ErrNoRows) {
		return s, false, nil
	}
	return s, err == nil, err
}

// PendingPatchnotes returns the entries to post now, oldest first: the ones asked from the admin page, and (when
// turned on) the ones that arrived since they were turned on, for the chosen scope.
func (db *DB) PendingPatchnotes(ctx context.Context) ([]Patchnote, error) {
	rows, err := db.Pool.Query(ctx, `
		SELECT p.id, p.component, p.version, p.title, COALESCE(p.released, ''), p.body, p.title_en, p.body_en, p.requested_at IS NOT NULL
		FROM patchnotes p, patchnote_settings s
		WHERE s.id = 1 AND p.posted_at IS NULL AND NOT p.baseline AND (p.requested_at IS NOT NULL
			OR (s.enabled AND s.since IS NOT NULL AND p.created_at >= s.since AND (s.scope = 'both' OR s.scope = p.component)))
		ORDER BY p.id LIMIT 20`)
	if err != nil {
		return nil, err
	}
	defer rows.Close()
	var out []Patchnote
	for rows.Next() {
		var p Patchnote
		if err := rows.Scan(&p.ID, &p.Component, &p.Version, &p.Title, &p.Released, &p.Body, &p.TitleEN, &p.BodyEN, &p.Requested); err != nil {
			return nil, err
		}
		out = append(out, p)
	}
	return out, rows.Err()
}

// ReservePatchnote books an entry before posting it: false when someone else already did (never posted twice).
func (db *DB) ReservePatchnote(ctx context.Context, id int64) (bool, error) {
	tag, err := db.Pool.Exec(ctx, `UPDATE patchnotes SET posted_at = $2 WHERE id = $1 AND posted_at IS NULL`, id, time.Now().UTC())
	if err != nil {
		return false, err
	}
	return tag.RowsAffected() == 1, nil
}

// FinishPatchnote records how the post went.
func (db *DB) FinishPatchnote(ctx context.Context, id int64, ok bool, detail string) error {
	_, err := db.Pool.Exec(ctx, `UPDATE patchnotes SET ok = $2, detail = NULLIF($3, '') WHERE id = $1`,
		id, ok, trim(detail, 300))
	return err
}
