package handlers

import (
	"context"
	"fmt"
	"log"
	"strconv"
	"time"

	"hourglass-bot/database"

	"github.com/bwmarrin/discordgo"
)

type BotHandler struct {
	DB *database.DB
}

func New(db *database.DB) *BotHandler {
	return &BotHandler{DB: db}
}

// OnReady est déclenché quand le bot se connecte à Discord
func (h *BotHandler) OnReady(s *discordgo.Session, r *discordgo.Ready) {
	log.Printf("🤖 Bot connecté en tant que %s#%s sur %d serveur(s)", s.State.User.Username, s.State.User.Discriminator, len(s.State.Guilds))

	// Demander le cache complet des membres et présences pour chaque serveur
	for _, g := range s.State.Guilds {
		_ = s.RequestGuildMembers(g.ID, "", 0, "", true)
	}

	// Lancer la réconciliation des sessions orphelines suite à un éventuel crash/redémarrage
	go h.reconcileSessions(s)

	// Lancer la boucle de Heartbeat & actualisation présences (toutes les 30s)
	go h.startHeartbeatLoop(s)
}

// OnMessageCreate enregistre chaque message textuel
func (h *BotHandler) OnMessageCreate(s *discordgo.Session, m *discordgo.MessageCreate) {
	// Ignorer les messages des bots et les DMs
	if m.Author == nil || m.Author.Bot || m.GuildID == "" {
		return
	}

	ctx, cancel := context.WithTimeout(context.Background(), 3*time.Second)
	defer cancel()

	userID, _ := strconv.ParseInt(m.Author.ID, 10, 64)
	serverID, _ := strconv.ParseInt(m.GuildID, 10, 64)
	channelID, _ := strconv.ParseInt(m.ChannelID, 10, 64)

	avatarURL := m.Author.AvatarURL("1024")

	log.Printf("💬 [MESSAGE] User %d (%s) a envoyé un message dans le salon %s", userID, m.Author.Username, m.ChannelID)

	// 1. Mise à jour utilisateur & message
	_ = h.DB.UpsertUser(ctx, userID, m.Author.Username, avatarURL)
	_ = h.DB.RecordMessageEvent(ctx, userID, serverID, channelID)

	// 2. Mise à jour des métadonnées du salon textuel
	if ch, err := s.State.Channel(m.ChannelID); err == nil {
		_ = h.DB.UpsertChannel(ctx, channelID, serverID, ch.Name, "text")
	}

	// 3. Mise à jour du nom du serveur
	if g, err := s.State.Guild(m.GuildID); err == nil {
		serverAvatar := g.IconURL("1024")
		_ = h.DB.UpsertServer(ctx, serverID, g.Name, serverAvatar)
	}
}

// OnVoiceStateUpdate gère les arrivées, départs et changements de salon en vocal
func (h *BotHandler) OnVoiceStateUpdate(s *discordgo.Session, v *discordgo.VoiceStateUpdate) {
	if v.VoiceState == nil || v.GuildID == "" {
		return
	}

	ctx, cancel := context.WithTimeout(context.Background(), 5*time.Second)
	defer cancel()

	userID, _ := strconv.ParseInt(v.UserID, 10, 64)
	serverID, _ := strconv.ParseInt(v.GuildID, 10, 64)

	// Métadonnées utilisateur
	if v.Member != nil && v.Member.User != nil {
		avatarURL := v.Member.User.AvatarURL("1024")
		_ = h.DB.UpsertUser(ctx, userID, v.Member.User.Username, avatarURL)
	}

	isStreaming := v.SelfStream
	isCameraOn := v.SelfVideo

	oldChannelID := ""
	if v.BeforeUpdate != nil {
		oldChannelID = v.BeforeUpdate.ChannelID
	}
	newChannelID := v.ChannelID

	// CAS 1 : Connexion à un salon vocal (rejoint depuis aucun salon)
	if oldChannelID == "" && newChannelID != "" {
		chID, _ := strconv.ParseInt(newChannelID, 10, 64)
		if ch, err := s.State.Channel(newChannelID); err == nil {
			_ = h.DB.UpsertChannel(ctx, chID, serverID, ch.Name, "voice")
		}
		if err := h.DB.StartVoiceSession(ctx, userID, serverID, chID, isStreaming, isCameraOn); err != nil {
			log.Printf("Erreur StartVoiceSession: %v", err)
		} else {
			log.Printf("🎙️ [VOCAL] User %d a rejoint le salon %s sur le serveur %d", userID, newChannelID, serverID)
		}
		return
	}

	// CAS 2 : Déconnexion complète du vocal
	if oldChannelID != "" && newChannelID == "" {
		if _, err := h.DB.EndVoiceSession(ctx, userID, serverID); err != nil {
			log.Printf("Erreur EndVoiceSession: %v", err)
		} else {
			log.Printf("👋 [VOCAL] User %d a quitté le vocal sur le serveur %d", userID, serverID)
		}
		return
	}

	// CAS 3 : Changement de salon vocal (switch direct)
	if oldChannelID != "" && newChannelID != "" && oldChannelID != newChannelID {
		newChID, _ := strconv.ParseInt(newChannelID, 10, 64)
		if ch, err := s.State.Channel(newChannelID); err == nil {
			_ = h.DB.UpsertChannel(ctx, newChID, serverID, ch.Name, "voice")
		}
		if err := h.DB.SwitchVoiceChannel(ctx, userID, serverID, newChID, isStreaming, isCameraOn); err != nil {
			log.Printf("Erreur SwitchVoiceChannel: %v", err)
		} else {
			log.Printf("🔀 [VOCAL] User %d a changé de salon (%s -> %s) sur le serveur %d", userID, oldChannelID, newChannelID, serverID)
		}
		return
	}
}

// OnPresenceUpdate met à jour le statut en ligne/absent/dnd d'un membre
func (h *BotHandler) OnPresenceUpdate(s *discordgo.Session, p *discordgo.PresenceUpdate) {
	if p.User == nil {
		return
	}
	userID, err := strconv.ParseInt(p.User.ID, 10, 64)
	if err != nil {
		return
	}
	ctx, cancel := context.WithTimeout(context.Background(), 2*time.Second)
	defer cancel()
	_ = h.DB.UpsertUserPresence(ctx, userID, string(p.Status))
}

// startHeartbeatLoop met à jour périodiquement les heartbeats et le statut de présence des serveurs
func (h *BotHandler) startHeartbeatLoop(s *discordgo.Session) {
	ticker := time.NewTicker(30 * time.Second)
	defer ticker.Stop()

	// Exécuter immédiatement une première fois
	h.refreshServerPresences(s)

	for range ticker.C {
		ctx, cancel := context.WithTimeout(context.Background(), 5*time.Second)
		updated, err := h.DB.UpdateHeartbeats(ctx)
		cancel()
		if err != nil {
			log.Printf("⚠️ Erreur Heartbeat: %v", err)
		} else if updated > 0 {
			log.Printf("💓 Heartbeat actualisé pour %d session(s) active(s)", updated)
		}

		h.refreshServerPresences(s)
	}
}

func (h *BotHandler) refreshServerPresences(s *discordgo.Session) {
	ctx, cancel := context.WithTimeout(context.Background(), 10*time.Second)
	defer cancel()

	for _, g := range s.State.Guilds {
		guild, err := s.State.Guild(g.ID)
		if err != nil {
			continue
		}
		online, idle, dnd, offline := 0, 0, 0, 0
		for _, p := range guild.Presences {
			switch p.Status {
			case discordgo.StatusOnline:
				online++
			case discordgo.StatusIdle:
				idle++
			case discordgo.StatusDoNotDisturb:
				dnd++
			default:
				offline++
			}
			if p.User != nil {
				uID, _ := strconv.ParseInt(p.User.ID, 10, 64)
				_ = h.DB.UpsertUserPresence(ctx, uID, string(p.Status))
			}
		}

		voiceCount := 0
		for _, vs := range guild.VoiceStates {
			if vs.ChannelID != "" {
				voiceCount++
			}
		}

		serverID, _ := strconv.ParseInt(g.ID, 10, 64)
		_ = h.DB.UpdateLiveServerStatus(ctx, serverID, online, idle, dnd, offline, voiceCount)
		_ = h.DB.UpsertServer(ctx, serverID, guild.Name, guild.IconURL("1024"))
	}
}

// OnGuildCreate est déclenché quand le bot rejoint un serveur ou au démarrage
func (h *BotHandler) OnGuildCreate(s *discordgo.Session, g *discordgo.GuildCreate) {
	if g.Guild == nil {
		return
	}
	ctx, cancel := context.WithTimeout(context.Background(), 5*time.Second)
	defer cancel()

	serverID, _ := strconv.ParseInt(g.ID, 10, 64)
	avatarURL := g.IconURL("1024")
	_ = h.DB.UpsertServer(ctx, serverID, g.Name, avatarURL)
	log.Printf("📥 [GUILD] Bot présent sur le serveur %d (%s)", serverID, g.Name)
}

// OnGuildDelete est déclenché quand le bot est retiré d'un serveur (kické, banni ou quitte)
func (h *BotHandler) OnGuildDelete(s *discordgo.Session, g *discordgo.GuildDelete) {
	if g.Guild == nil {
		return
	}
	ctx, cancel := context.WithTimeout(context.Background(), 5*time.Second)
	defer cancel()

	serverID, _ := strconv.ParseInt(g.ID, 10, 64)
	_ = h.DB.SetServerBotPresence(ctx, serverID, false)
	log.Printf("📤 [GUILD] Bot retiré du serveur %d (%s) - Historique préservé", serverID, g.Name)
}

// reconcileSessions inspecte les salons réels de Discord au boot et clôture les sessions fantômes
func (h *BotHandler) reconcileSessions(s *discordgo.Session) {
	ctx, cancel := context.WithTimeout(context.Background(), 15*time.Second)
	defer cancel()

	activeSessions, err := h.DB.GetActiveVoiceSessions(ctx)
	if err != nil {
		log.Printf("Erreur récupération sessions actives pour réconciliation: %v", err)
		return
	}

	if len(activeSessions) == 0 {
		return
	}

	log.Printf("🔍 Réconciliation : %d session(s) active(s) en BDD à vérifier...", len(activeSessions))

	// Construire une map des membres réellement en vocal sur Discord par (guildID, userID)
	realVoiceMembers := make(map[string]bool)
	for _, g := range s.State.Guilds {
		guild, err := s.State.Guild(g.ID)
		if err != nil {
			continue
		}
		for _, vs := range guild.VoiceStates {
			if vs.ChannelID != "" {
				key := fmt.Sprintf("%s:%s", vs.GuildID, vs.UserID)
				realVoiceMembers[key] = true
			}
		}
	}

	reconciledCount := 0
	for _, sess := range activeSessions {
		key := fmt.Sprintf("%d:%d", sess.ServerID, sess.UserID)
		if !realVoiceMembers[key] {
			// L'utilisateur n'est plus en vocal : on clôture à la date de son dernier heartbeat
			closeTime := time.Now()
			if sess.LastHeartbeat != nil {
				closeTime = *sess.LastHeartbeat
			}
			_ = h.DB.CloseOrphanSession(ctx, sess.SessionID, closeTime)
			reconciledCount++
		}
	}

	if reconciledCount > 0 {
		log.Printf("✅ Réconciliation terminée : %d session(s) orpheline(s) clôturée(s) proprement.", reconciledCount)
	}
}
