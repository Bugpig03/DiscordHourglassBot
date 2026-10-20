package main

import (
	"context"
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
	log.Println("🚀 Démarrage de Hourglass Bot v3.2.0 (Go Edition)...")

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
