package main

import (
	"context"
	"io"
	"log"
	"os"
	"os/signal"
	"syscall"
	"time"

	"hourglass-bot/config"
	"hourglass-bot/database"
	"hourglass-bot/handlers"

	"github.com/bwmarrin/discordgo"
)

func main() {
	log.Printf("🚀 Démarrage de Hourglass Bot v%s (Go Edition, build %s)...", handlers.Version, handlers.BuildDate)

	// 1. Chargement de la configuration
	cfg, err := config.LoadConfig()
	if err != nil {
		log.Fatalf("❌ Erreur de configuration: %v", err)
	}

	// 2. Connexion à PostgreSQL via pgxpool
	db, err := database.New(cfg.DatabaseURL())
	if err != nil {
		log.Fatalf("❌ Erreur de connexion à PostgreSQL: %v", err)
	}
	defer db.Close()

	// Table of slash command usage (read by the website admin page), created when the migration was not applied
	ensureCtx, ensureCancel := context.WithTimeout(context.Background(), 10*time.Second)
	if err := db.EnsureCommandEventsTable(ensureCtx); err != nil {
		log.Printf("⚠️ Suivi des commandes désactivé (table bot_command_events indisponible): %v", err)
	}
	// Unique members present on the servers (admin page), same principle
	if err := db.EnsureMemberSnapshotsTable(ensureCtx); err != nil {
		log.Printf("⚠️ Comptage des membres uniques désactivé (table bot_member_snapshots indisponible): %v", err)
	}
	// Bots and apps flagged in users (BOT tag and ranking filter of the website)
	if err := db.EnsureUsersBotColumn(ensureCtx); err != nil {
		log.Printf("⚠️ Repérage des bots désactivé (colonne users.is_bot indisponible): %v", err)
	}
	// Copy of each server for the website (server management page): owner, channels, roles, members, journal
	if err := db.EnsureGuildStateTables(ensureCtx); err != nil {
		log.Printf("⚠️ Copie des serveurs pour le site désactivée (tables guild_* indisponibles): %v", err)
	}
	// Level-up announcements: settings (written by the website) and last level seen per member
	if err := db.EnsureLevelupTables(ensureCtx); err != nil {
		log.Printf("⚠️ Annonces de niveau désactivées (tables server_levelup / levelup_state indisponibles): %v", err)
	}
	// Automatic reports: settings, reports sent (never twice) and tests asked from the website
	if err := db.EnsureReportTables(ensureCtx); err != nil {
		log.Printf("⚠️ Rapports automatiques désactivés (tables server_reports / report_runs indisponibles): %v", err)
	}
	// Automatic roles: settings and rules (written by the website) and the roles the bot gave
	if err := db.EnsureRoleTables(ensureCtx); err != nil {
		log.Printf("⚠️ Rôles automatiques désactivés (tables server_roles / role_grants indisponibles): %v", err)
	}
	// Log lines copied to bot_logs as well (website admin page, "Logs du bot")
	if err := db.EnsureBotLogsTable(ensureCtx); err != nil {
		log.Printf("⚠️ Copie des logs en base désactivée (table bot_logs indisponible): %v", err)
	} else {
		logs := db.NewLogWriter()
		log.SetOutput(io.MultiWriter(os.Stderr, logs))
		defer logs.Close()
	}
	ensureCancel()

	// 3. Initialisation de la session DiscordGo
	dg, err := discordgo.New("Bot " + cfg.DiscordToken)
	if err != nil {
		log.Fatalf("❌ Erreur d'initialisation Discord: %v", err)
	}

	// Configurer tous les intents nécessaires
	dg.Identify.Intents = discordgo.IntentsAll

	// 4. Enregistrement des écouteurs d'événements
	h := handlers.New(db)
	dg.AddHandler(h.OnReady)
	dg.AddHandler(h.OnMessageCreate)
	dg.AddHandler(h.OnVoiceStateUpdate)
	dg.AddHandler(h.OnPresenceUpdate)
	dg.AddHandler(h.OnGuildCreate)
	dg.AddHandler(h.OnGuildDelete)
	dg.AddHandler(h.OnInteractionCreate)
	// Copie des serveurs pour le site : membres, propriétaire, salons et rôles
	dg.AddHandler(h.OnGuildMembersChunk)
	dg.AddHandler(h.OnGuildMemberAdd)
	dg.AddHandler(h.OnGuildMemberRemove)
	dg.AddHandler(h.OnGuildMemberUpdate)
	dg.AddHandler(h.OnGuildUpdate)
	dg.AddHandler(h.OnChannelCreate)
	dg.AddHandler(h.OnChannelUpdate)
	dg.AddHandler(h.OnChannelDelete)
	dg.AddHandler(h.OnGuildRoleCreate)
	dg.AddHandler(h.OnGuildRoleUpdate)
	dg.AddHandler(h.OnGuildRoleDelete)

	// 5. Connexion à la Gateway Discord
	if err := dg.Open(); err != nil {
		log.Fatalf("❌ Erreur de connexion à Discord Gateway: %v", err)
	}
	defer dg.Close()

	// Enregistrement des commandes slash
	h.RegisterSlashCommands(dg)

	log.Println("⏳ Bot Hourglass opérationnel. En attente d'événements (Ctrl+C pour arrêter)...")

	// Attente d'un signal d'arrêt gracieux
	sc := make(chan os.Signal, 1)
	signal.Notify(sc, syscall.SIGINT, syscall.SIGTERM, os.Interrupt)
	<-sc

	log.Println("🛑 Arrêt du bot en cours...")
}
