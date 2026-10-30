package database

import (
	"context"
	"fmt"
	"log"
	"time"

	"github.com/jackc/pgx/v5"
	"github.com/jackc/pgx/v5/pgxpool"
)

type DB struct {
	Pool *pgxpool.Pool
	// hasBotColumn is set once users.is_bot exists (EnsureUsersBotColumn): until then UpsertUser keeps
	// its former query, so a missing column never stops members from being recorded
	hasBotColumn bool
}

func New(connStr string) (*DB, error) {
	ctx, cancel := context.WithTimeout(context.Background(), 10*time.Second)
	defer cancel()

	config, err := pgxpool.ParseConfig(connStr)
	if err != nil {
		return nil, fmt.Errorf("erreur configuration pgxpool: %w", err)
	}

	config.MaxConns = 25
	config.MinConns = 5
	config.MaxConnLifetime = 30 * time.Minute
	config.MaxConnIdleTime = 5 * time.Minute
	config.AfterConnect = func(ctx context.Context, conn *pgx.Conn) error {
		_, err := conn.Exec(ctx, "SET TIME ZONE 'UTC'")
		return err
	}

	pool, err := pgxpool.NewWithConfig(ctx, config)
	if err != nil {
		return nil, fmt.Errorf("impossible de créer le pool PostgreSQL: %w", err)
	}

	if err := pool.Ping(ctx); err != nil {
		return nil, fmt.Errorf("ping base de données échoué: %w", err)
	}

	log.Println("✅ Pool PostgreSQL connecté et prêt.")
	return &DB{Pool: pool}, nil
}

func (db *DB) Close() {
	if db.Pool != nil {
		db.Pool.Close()
	}
}

// UpsertUser insère ou met à jour les informations d'un utilisateur (isBot : compte bot ou application,
// jamais retiré une fois posé)
func (db *DB) UpsertUser(ctx context.Context, userID int64, username, avatar string, isBot bool) error {
	if db.hasBotColumn {
		_, err := db.Pool.Exec(ctx, `
			INSERT INTO users (user_id, username, avatar, is_bot)
			VALUES ($1, $2, $3, $4)
			ON CONFLICT (user_id) DO UPDATE
			SET username = EXCLUDED.username,
			    avatar = COALESCE(EXCLUDED.avatar, users.avatar),
			    is_bot = users.is_bot OR EXCLUDED.is_bot
			WHERE users.username IS DISTINCT FROM EXCLUDED.username
			   OR users.avatar IS DISTINCT FROM COALESCE(EXCLUDED.avatar, users.avatar)
			   OR (EXCLUDED.is_bot AND NOT users.is_bot)
		`, userID, username, avatar, isBot)
		return err
	}
	query := `
		INSERT INTO users (user_id, username, avatar)
		VALUES ($1, $2, $3)
		ON CONFLICT (user_id) DO UPDATE
		SET username = EXCLUDED.username,
		    avatar = COALESCE(EXCLUDED.avatar, users.avatar)
		WHERE users.username IS DISTINCT FROM EXCLUDED.username
		   OR users.avatar IS DISTINCT FROM COALESCE(EXCLUDED.avatar, users.avatar)
	`
	_, err := db.Pool.Exec(ctx, query, userID, username, avatar)
	return err
}

// UpsertServer insère ou met à jour les informations d'un serveur et confirme la présence du bot
func (db *DB) UpsertServer(ctx context.Context, serverID int64, servername, avatar string) error {
	query := `
		INSERT INTO servers (server_id, servername, avatar, is_bot_present, first_tracked_at)
		VALUES ($1, $2, $3, TRUE, NOW())
		ON CONFLICT (server_id) DO UPDATE
		SET servername = EXCLUDED.servername,
		    avatar = COALESCE(EXCLUDED.avatar, servers.avatar),
		    is_bot_present = TRUE,
		    left_at = NULL
		WHERE servers.servername IS DISTINCT FROM EXCLUDED.servername
		   OR servers.avatar IS DISTINCT FROM COALESCE(EXCLUDED.avatar, servers.avatar)
		   OR servers.is_bot_present IS DISTINCT FROM TRUE
		   OR servers.left_at IS NOT NULL
	`
	_, err := db.Pool.Exec(ctx, query, serverID, servername, avatar)
	return err
}

// SetServerBotPresence met à jour l'état de présence du bot sur un serveur
func (db *DB) SetServerBotPresence(ctx context.Context, serverID int64, isPresent bool) error {
	var query string
	if isPresent {
		query = `UPDATE servers SET is_bot_present = TRUE, left_at = NULL WHERE server_id = $1`
	} else {
		query = `UPDATE servers SET is_bot_present = FALSE, left_at = NOW() WHERE server_id = $1`
	}
	_, err := db.Pool.Exec(ctx, query, serverID)
	return err
}

// RecordPresenceHistory insère un instantané dans presence_history
func (db *DB) RecordPresenceHistory(ctx context.Context, serverID *int64, online, idle, dnd, offline int) error {
	query := `
		INSERT INTO presence_history (server_id, online_count, idle_count, dnd_count, offline_count, recorded_at)
		VALUES ($1, $2, $3, $4, $5, NOW())
	`
	_, err := db.Pool.Exec(ctx, query, serverID, online, idle, dnd, offline)
	return err
}

// PurgePerServerPresenceHistory supprime les instantanés par serveur, qui ne sont plus enregistrés
// (seul l'instantané global, server_id NULL, est lu par le site). Par lots de 50 000 lignes pour
// ne pas verrouiller la table longtemps ; renvoie le nombre de lignes supprimées.
func (db *DB) PurgePerServerPresenceHistory(ctx context.Context) (int64, error) {
	var total int64
	for {
		tag, err := db.Pool.Exec(ctx, `
			DELETE FROM presence_history
			WHERE id IN (SELECT id FROM presence_history WHERE server_id IS NOT NULL LIMIT 50000)`)
		if err != nil {
			return total, err
		}
		total += tag.RowsAffected()
		if tag.RowsAffected() == 0 {
			return total, nil
		}
	}
}

// CleanOldPresenceHistory supprime les instantanés de présence datant de plus de 7 jours
func (db *DB) CleanOldPresenceHistory(ctx context.Context) error {
	query := `DELETE FROM presence_history WHERE recorded_at < NOW() - INTERVAL '7 days'`
	_, err := db.Pool.Exec(ctx, query)
	return err
}

// UpsertChannel insère ou met à jour le nom et le type d'un salon
func (db *DB) UpsertChannel(ctx context.Context, channelID, serverID int64, name, channelType string) error {
	query := `
		INSERT INTO channels (channel_id, server_id, name, type, last_updated)
		VALUES ($1, $2, $3, $4, NOW())
		ON CONFLICT (channel_id) DO UPDATE
		SET name = EXCLUDED.name,
		    type = EXCLUDED.type,
		    last_updated = NOW()
	`
	_, err := db.Pool.Exec(ctx, query, channelID, serverID, name, channelType)
	return err
}

// StartVoiceSession ouvre une nouvelle session vocale
func (db *DB) StartVoiceSession(ctx context.Context, userID, serverID, channelID int64, isStreaming, isCameraOn bool) error {
	query := `
		INSERT INTO voice_sessions (user_id, server_id, channel_id, joined_at, last_heartbeat, is_streaming, is_camera_on)
		VALUES ($1, $2, $3, NOW(), NOW(), $4, $5)
	`
	_, err := db.Pool.Exec(ctx, query, userID, serverID, channelID, isStreaming, isCameraOn)
	return err
}

// EndVoiceSession clôture une session vocale active, calcule sa durée et synchronise stats
func (db *DB) EndVoiceSession(ctx context.Context, userID, serverID int64) (int, error) {
	query := `
		UPDATE voice_sessions
		SET left_at = NOW(),
		    duration_seconds = GREATEST(0, EXTRACT(EPOCH FROM (NOW() - joined_at))::INT)
		WHERE user_id = $1 AND server_id = $2 AND left_at IS NULL
		RETURNING duration_seconds
	`
	var duration int
	err := db.Pool.QueryRow(ctx, query, userID, serverID).Scan(&duration)
	if err == nil && duration > 0 {
		// Mettre à jour également la table stats pour cohérence totale
		_ = db.AddSecondsToStats(ctx, userID, serverID, duration)
	}
	return duration, err
}

// AddSecondsToStats incrémente les secondes dans la table historique stats
func (db *DB) AddSecondsToStats(ctx context.Context, userID, serverID int64, seconds int) error {
	query := `
		INSERT INTO stats (user_id, server_id, messages, seconds, score, date_creation)
		VALUES ($1, $2, 0, $3, 0, NOW())
		ON CONFLICT (user_id, server_id) DO UPDATE
		SET seconds = stats.seconds + EXCLUDED.seconds
	`
	_, err := db.Pool.Exec(ctx, query, userID, serverID, seconds)
	return err
}

// AddMessagesToStats incrémente les messages dans la table historique stats
func (db *DB) AddMessagesToStats(ctx context.Context, userID, serverID int64) error {
	query := `
		INSERT INTO stats (user_id, server_id, messages, seconds, score, date_creation)
		VALUES ($1, $2, 1, 0, 0, NOW())
		ON CONFLICT (user_id, server_id) DO UPDATE
		SET messages = stats.messages + 1
	`
	_, err := db.Pool.Exec(ctx, query, userID, serverID)
	return err
}

// SwitchVoiceChannel ferme la session du salon précédent et ouvre immédiatement celle du nouveau salon en une seule transaction
func (db *DB) SwitchVoiceChannel(ctx context.Context, userID, serverID, newChannelID int64, isStreaming, isCameraOn bool) error {
	tx, err := db.Pool.Begin(ctx)
	if err != nil {
		return err
	}
	defer tx.Rollback(ctx)

	// Clôturer la session en cours et récupérer la durée
	closeQuery := `
		UPDATE voice_sessions
		SET left_at = NOW(),
		    duration_seconds = GREATEST(0, EXTRACT(EPOCH FROM (NOW() - joined_at))::INT)
		WHERE user_id = $1 AND server_id = $2 AND left_at IS NULL
		RETURNING duration_seconds
	`
	var duration int
	if err := tx.QueryRow(ctx, closeQuery, userID, serverID).Scan(&duration); err == nil && duration > 0 {
		// Synchroniser stats
		syncStats := `
			INSERT INTO stats (user_id, server_id, messages, seconds, score, date_creation)
			VALUES ($1, $2, 0, $3, 0, NOW())
			ON CONFLICT (user_id, server_id) DO UPDATE
			SET seconds = stats.seconds + EXCLUDED.seconds
		`
		_, _ = tx.Exec(ctx, syncStats, userID, serverID, duration)
	}

	// Ouvrir la nouvelle session
	openQuery := `
		INSERT INTO voice_sessions (user_id, server_id, channel_id, joined_at, last_heartbeat, is_streaming, is_camera_on)
		VALUES ($1, $2, $3, NOW(), NOW(), $4, $5)
	`
	if _, err := tx.Exec(ctx, openQuery, userID, serverID, newChannelID, isStreaming, isCameraOn); err != nil {
		return err
	}

	return tx.Commit(ctx)
}

// SyncVoiceSession synchronise ou réactive la session vocale d'un membre présent dans un salon
func (db *DB) SyncVoiceSession(ctx context.Context, userID, serverID, channelID int64, isStreaming, isCameraOn bool) error {
	// 1. Session déjà active (left_at IS NULL) ?
	var activeID int64
	var activeChannelID *int64
	err := db.Pool.QueryRow(ctx, `
		SELECT session_id, channel_id 
		FROM voice_sessions 
		WHERE user_id = $1 AND server_id = $2 AND left_at IS NULL
		LIMIT 1
	`, userID, serverID).Scan(&activeID, &activeChannelID)

	if err == nil {
		if activeChannelID != nil && *activeChannelID == channelID {
			_, errTouch := db.Pool.Exec(ctx, `
				UPDATE voice_sessions 
				SET last_heartbeat = NOW(), is_streaming = $2, is_camera_on = $3 
				WHERE session_id = $1
			`, activeID, isStreaming, isCameraOn)
			return errTouch
		}
		// Salon différent : bascule
		return db.SwitchVoiceChannel(ctx, userID, serverID, channelID, isStreaming, isCameraOn)
	}

	// 2. Session clôturée à tort par la réconciliation (crash, serveur momentanément indisponible) ?
	// Seules les sessions orphelines (left_at = last_heartbeat, cf. CloseOrphanSession) dans le même salon
	// sont rouvertes : une déconnexion normale suivie d'un retour ne doit jamais compter l'absence comme du vocal.
	reopened, err := db.reopenOrphanSession(ctx, userID, serverID, channelID, isStreaming, isCameraOn)
	if err != nil {
		log.Printf("⚠️ Réouverture de session orpheline impossible (user %d): %v", userID, err)
	}
	if reopened {
		return nil
	}

	// 3. Sinon, ouvrir une nouvelle session vocale
	return db.StartVoiceSession(ctx, userID, serverID, channelID, isStreaming, isCameraOn)
}

// reopenOrphanSession rouvre la dernière session orpheline récente et retire de stats la durée qui y avait été ajoutée
func (db *DB) reopenOrphanSession(ctx context.Context, userID, serverID, channelID int64, isStreaming, isCameraOn bool) (bool, error) {
	tx, err := db.Pool.Begin(ctx)
	if err != nil {
		return false, err
	}
	defer tx.Rollback(ctx)

	var previousDuration int
	err = tx.QueryRow(ctx, `
		WITH target AS (
			SELECT session_id, duration_seconds
			FROM voice_sessions
			WHERE user_id = $1 AND server_id = $2 AND channel_id = $3
			  AND left_at IS NOT NULL
			  AND left_at = last_heartbeat
			  AND left_at >= NOW() - INTERVAL '2 hours'
			  AND NOT is_legacy
			ORDER BY left_at DESC
			LIMIT 1
			FOR UPDATE
		)
		UPDATE voice_sessions v
		SET left_at = NULL, duration_seconds = 0, last_heartbeat = NOW(), is_streaming = $4, is_camera_on = $5
		FROM target
		WHERE v.session_id = target.session_id
		RETURNING target.duration_seconds
	`, userID, serverID, channelID, isStreaming, isCameraOn).Scan(&previousDuration)
	if err == pgx.ErrNoRows {
		return false, nil
	}
	if err != nil {
		return false, err
	}

	// La durée sera recomptée en entier à la prochaine clôture : on l'annule dans stats pour éviter un double comptage
	if previousDuration > 0 {
		if _, err := tx.Exec(ctx, `
			UPDATE stats SET seconds = GREATEST(0, seconds - $3)
			WHERE user_id = $1 AND server_id = $2
		`, userID, serverID, previousDuration); err != nil {
			return false, err
		}
	}

	return true, tx.Commit(ctx)
}

// UpdateVoiceSessionFlags met à jour l'état stream/caméra de la session vocale active
func (db *DB) UpdateVoiceSessionFlags(ctx context.Context, userID, serverID int64, isStreaming, isCameraOn bool) error {
	_, err := db.Pool.Exec(ctx, `
		UPDATE voice_sessions
		SET is_streaming = $3, is_camera_on = $4
		WHERE user_id = $1 AND server_id = $2 AND left_at IS NULL
	`, userID, serverID, isStreaming, isCameraOn)
	return err
}

// UpsertUserPresence enregistre le statut de présence Discord d'un utilisateur
func (db *DB) UpsertUserPresence(ctx context.Context, userID int64, status string) error {
	query := `
		INSERT INTO user_presence (user_id, status, last_updated)
		VALUES ($1, $2, NOW())
		ON CONFLICT (user_id) DO UPDATE
		SET status = EXCLUDED.status,
		    last_updated = NOW()
	`
	_, err := db.Pool.Exec(ctx, query, userID, status)
	return err
}

// BulkUpsertUserPresence enregistre les statuts de nombreux utilisateurs en une seule requête.
// Seules les lignes dont le statut a réellement changé sont réécrites (pas de WAL ni de tuples morts inutiles).
func (db *DB) BulkUpsertUserPresence(ctx context.Context, userIDs []int64, statuses []string) error {
	if len(userIDs) == 0 {
		return nil
	}
	query := `
		INSERT INTO user_presence (user_id, status, last_updated)
		SELECT u, s, NOW() FROM unnest($1::BIGINT[], $2::VARCHAR[]) AS t(u, s)
		ON CONFLICT (user_id) DO UPDATE
		SET status = EXCLUDED.status,
		    last_updated = NOW()
		WHERE user_presence.status IS DISTINCT FROM EXCLUDED.status
	`
	_, err := db.Pool.Exec(ctx, query, userIDs, statuses)
	return err
}

// UpdateHeartbeats met à jour l'horodatage heartbeat pour toutes les sessions actives
func (db *DB) UpdateHeartbeats(ctx context.Context) (int64, error) {
	tag, err := db.Pool.Exec(ctx, `
		UPDATE voice_sessions
		SET last_heartbeat = NOW()
		WHERE left_at IS NULL
	`)
	if err != nil {
		return 0, err
	}
	return tag.RowsAffected(), nil
}

// RecordMessageEvent enregistre l'envoi d'un message horodaté et synchronise stats
func (db *DB) RecordMessageEvent(ctx context.Context, userID, serverID, channelID int64) error {
	query := `
		INSERT INTO message_events (user_id, server_id, channel_id, created_at, count)
		VALUES ($1, $2, $3, NOW(), 1)
	`
	_, err := db.Pool.Exec(ctx, query, userID, serverID, channelID)
	if err == nil {
		_ = db.AddMessagesToStats(ctx, userID, serverID)
	}
	return err
}

// UpdateLiveServerStatus met à jour les compteurs de présence en direct d'un serveur
func (db *DB) UpdateLiveServerStatus(ctx context.Context, serverID int64, online, idle, dnd, offline, voice int) error {
	query := `
		INSERT INTO live_server_status (server_id, online_count, idle_count, dnd_count, offline_count, voice_count, updated_at)
		VALUES ($1, $2, $3, $4, $5, $6, NOW())
		ON CONFLICT (server_id) DO UPDATE
		SET online_count = EXCLUDED.online_count,
		    idle_count = EXCLUDED.idle_count,
		    dnd_count = EXCLUDED.dnd_count,
		    offline_count = EXCLUDED.offline_count,
		    voice_count = EXCLUDED.voice_count,
		    updated_at = NOW()
	`
	_, err := db.Pool.Exec(ctx, query, serverID, online, idle, dnd, offline, voice)
	return err
}

// ActiveSession représente une session active en base
type ActiveSession struct {
	SessionID     int64
	UserID        int64
	ServerID      int64
	ChannelID     *int64
	JoinedAt      time.Time
	LastHeartbeat *time.Time
}

// GetActiveVoiceSessions récupère toutes les sessions en cours (left_at IS NULL)
func (db *DB) GetActiveVoiceSessions(ctx context.Context) ([]ActiveSession, error) {
	rows, err := db.Pool.Query(ctx, `
		SELECT session_id, user_id, server_id, channel_id, joined_at, last_heartbeat
		FROM voice_sessions
		WHERE left_at IS NULL
	`)
	if err != nil {
		return nil, err
	}
	defer rows.Close()

	var sessions []ActiveSession
	for rows.Next() {
		var s ActiveSession
		if err := rows.Scan(&s.SessionID, &s.UserID, &s.ServerID, &s.ChannelID, &s.JoinedAt, &s.LastHeartbeat); err != nil {
			return nil, err
		}
		sessions = append(sessions, s)
	}
	return sessions, rows.Err()
}

// CloseOrphanSession clôture une session orpheline dont l'utilisateur a quitté pendant un crash.
// left_at = last_heartbeat sert de marqueur pour que SyncVoiceSession puisse la rouvrir si la clôture était erronée.
func (db *DB) CloseOrphanSession(ctx context.Context, sessionID int64, closeTime time.Time) error {
	query := `
		UPDATE voice_sessions
		SET left_at = $2,
		    last_heartbeat = $2,
		    duration_seconds = GREATEST(0, EXTRACT(EPOCH FROM ($2 - joined_at))::INT)
		WHERE session_id = $1 AND left_at IS NULL
		RETURNING user_id, server_id, duration_seconds
	`
	var userID, serverID int64
	var duration int
	// Colonnes TIMESTAMP sans fuseau stockées en UTC : on normalise pour ne pas décaler l'heure de clôture
	err := db.Pool.QueryRow(ctx, query, sessionID, closeTime.UTC()).Scan(&userID, &serverID, &duration)
	if err == nil && duration > 0 {
		_ = db.AddSecondsToStats(ctx, userID, serverID, duration)
	}
	return err
}
