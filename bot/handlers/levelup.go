package handlers

import (
	"context"
	"fmt"
	"log"
	"math"
	"strconv"
	"strings"
	"sync"
	"time"

	"hourglass-bot/card"
	"hourglass-bot/database"

	"github.com/bwmarrin/discordgo"
)

// Level-up announcements on the servers that turned them on (website, server management > Levels).
//
// The level is the member's level on that server, with the website's formula: 1 minute in voice = 1 XP,
// 1 message = 1 XP, level = floor(sqrt(XP / 100)) + 1 (votes belong to no server and do not count).
// It is checked after each message and, for members in voice, every 30 seconds (session in progress included).
// The first time a member is seen, their level is only recorded: levels reached before are never announced.

const (
	levelupReload   = time.Minute      // settings read again (changes on the website apply within a minute)
	levelupCooldown = 20 * time.Second // per member and server: a burst of messages is checked once
	levelupTimeout  = 15 * time.Second
	levelupMaxText  = 600
)

// levelFor is the level for an amount of activity (same formula as calculate_user_xp_and_level on the website).
func levelFor(seconds, messages int64) int {
	if seconds < 0 {
		seconds = 0
	}
	if messages < 0 {
		messages = 0
	}
	xp := seconds/60 + messages
	return int(math.Sqrt(float64(xp)/100)) + 1
}

// shouldAnnounce: a level between the previous one (excluded) and the new one (included) is at least min and a
// multiple of every (several levels at once: one announcement, of the new level).
func shouldAnnounce(prev, level, min, every int) bool {
	if every < 1 {
		every = 1
	}
	for k := prev + 1; k <= level; k++ {
		if k >= min && k%every == 0 {
			return true
		}
	}
	return false
}

type levelupManager struct {
	mu       sync.RWMutex
	settings map[int64]database.LevelupSettings
	seen     map[string]time.Time // "server:user" -> last check
	once     sync.Once
}

var levelups = &levelupManager{settings: map[int64]database.LevelupSettings{}, seen: map[string]time.Time{}}

// startLevelups loads the settings now and every minute (started once, whatever the reconnections).
func (h *BotHandler) startLevelups(s *discordgo.Session) {
	levelups.once.Do(func() {
		go func() {
			ticker := time.NewTicker(levelupReload)
			defer ticker.Stop()
			for {
				h.reloadLevelups()
				<-ticker.C
				h.checkVoiceLevelups(s)
			}
		}()
	})
}

func (h *BotHandler) reloadLevelups() {
	ctx, cancel := context.WithTimeout(context.Background(), 10*time.Second)
	defer cancel()
	settings, err := h.DB.LoadLevelupSettings(ctx)
	if err != nil {
		log.Printf("⚠️ [NIVEAUX] Réglages des annonces illisibles: %v", err)
		return
	}
	levelups.mu.Lock()
	levelups.settings = settings
	// forget old cooldowns
	for k, t := range levelups.seen {
		if time.Since(t) > time.Hour {
			delete(levelups.seen, k)
		}
	}
	levelups.mu.Unlock()
}

func (m *levelupManager) get(serverID int64) (database.LevelupSettings, bool) {
	m.mu.RLock()
	defer m.mu.RUnlock()
	s, ok := m.settings[serverID]
	return s, ok
}

// due tells whether this member may be checked now (one check per cooldown).
func (m *levelupManager) due(serverID, userID int64) bool {
	key := fmt.Sprintf("%d:%d", serverID, userID)
	m.mu.Lock()
	defer m.mu.Unlock()
	if t, ok := m.seen[key]; ok && time.Since(t) < levelupCooldown {
		return false
	}
	m.seen[key] = time.Now()
	return true
}

// checkVoiceLevelups looks at the members in voice on the servers with announcements (called every minute).
func (h *BotHandler) checkVoiceLevelups(s *discordgo.Session) {
	levelups.mu.RLock()
	servers := make([]int64, 0, len(levelups.settings))
	for id := range levelups.settings {
		servers = append(servers, id)
	}
	levelups.mu.RUnlock()
	for _, serverID := range servers {
		guild, err := s.State.Guild(strconv.FormatInt(serverID, 10))
		if err != nil || guild == nil {
			continue
		}
		for _, vs := range guild.VoiceStates {
			if vs.ChannelID == "" || vs.Member != nil && vs.Member.User != nil && vs.Member.User.Bot {
				continue
			}
			if userID, err := strconv.ParseInt(vs.UserID, 10, 64); err == nil {
				h.checkLevelup(s, serverID, userID, "")
			}
		}
	}
}

// checkLevelup compares the member's level with the last one seen, and announces a new one.
// sourceChannel is the channel the member just wrote in ("" for voice).
func (h *BotHandler) checkLevelup(s *discordgo.Session, serverID, userID int64, sourceChannel string) {
	settings, ok := levelups.get(serverID)
	if !ok || !levelups.due(serverID, userID) {
		return
	}
	ctx, cancel := context.WithTimeout(context.Background(), levelupTimeout)
	defer cancel()

	seconds, messages, err := h.DB.MemberServerActivity(ctx, userID, serverID)
	if err != nil {
		return
	}
	level := levelFor(seconds, messages)
	prev, found, err := h.DB.LevelupState(ctx, serverID, userID)
	if err != nil {
		return
	}
	if !found || level <= prev {
		if !found {
			_ = h.DB.SetLevelupState(ctx, serverID, userID, level, false)
		}
		return
	}
	announce := shouldAnnounce(prev, level, settings.MinLevel, settings.Every)
	// Recorded first: whatever happens to the message, a level is never announced twice
	if err := h.DB.SetLevelupState(ctx, serverID, userID, level, announce); err != nil || !announce {
		return
	}
	h.sendLevelup(ctx, s, settings, userID, level, sourceChannel)
}

func (h *BotHandler) sendLevelup(ctx context.Context, s *discordgo.Session, settings database.LevelupSettings, userID int64, level int, sourceChannel string) {
	guildID := strconv.FormatInt(settings.ServerID, 10)
	userIDStr := strconv.FormatInt(userID, 10)
	channelID := ""
	if settings.SameChannel && sourceChannel != "" {
		channelID = sourceChannel
	} else if settings.ChannelID != 0 {
		channelID = strconv.FormatInt(settings.ChannelID, 10)
	}
	logEntry := database.FeatureLog{ServerID: settings.ServerID, Feature: "levels", Action: "announce", TargetID: userID,
		OK: true, Detail: fmt.Sprintf("%d", level)}
	if channelID == "" {
		logEntry.OK, logEntry.Detail = false, fmt.Sprintf("%d · no channel", level)
		_ = h.DB.LogFeature(ctx, logEntry)
		return
	}

	name := userIDStr
	if m, err := s.State.Member(guildID, userIDStr); err == nil && m != nil && m.User != nil {
		name = m.Nick
		if name == "" {
			name = m.User.GlobalName
		}
		if name == "" {
			name = m.User.Username
		}
	}
	serverName := ""
	if g, err := s.State.Guild(guildID); err == nil && g != nil {
		serverName = g.Name
	}
	who := "**" + escapeMarkdown(name) + "**"
	if settings.Mention {
		who = "<@" + userIDStr + ">"
	}
	langCode := guildLang(settings.Locale)
	template := strings.TrimSpace(settings.Message)
	if template == "" {
		template = messages["levelup_default"][langCode]
	}
	text := strings.NewReplacer("{membre}", who, "{member}", who, "{niveau}", strconv.Itoa(level), "{level}", strconv.Itoa(level),
		"{serveur}", escapeMarkdown(serverName), "{server}", escapeMarkdown(serverName)).Replace(template)
	if r := []rune(text); len(r) > levelupMaxText {
		text = string(r[:levelupMaxText])
	}

	send := &discordgo.MessageSend{
		Content: text,
		// Only the member may be pinged, never @everyone, @here or a role written in the message
		AllowedMentions: &discordgo.MessageAllowedMentions{Parse: []discordgo.AllowedMentionType{}, Users: []string{}},
	}
	if settings.Mention {
		send.AllowedMentions.Users = []string{userIDStr}
	}
	// The card is the image of an embed, loaded by Discord from the website (signed address): no file to attach,
	// only the "Embed links" permission
	if settings.WithCard {
		if image := card.LevelupImageURL(userID, settings.ServerID, level, settings.Locale); image != "" {
			send.Embeds = []*discordgo.MessageEmbed{{Color: 0x717cf8, Image: &discordgo.MessageEmbedImage{URL: image}}}
		}
	}
	if _, err := s.ChannelMessageSendComplex(channelID, send, discordgo.WithContext(ctx)); err != nil {
		logEntry.OK = false
		logEntry.Detail = fmt.Sprintf("%d · %s", level, discordError(err))
		log.Printf("⚠️ [NIVEAUX] Annonce impossible sur %s (salon %s): %v", guildID, channelID, err)
	} else {
		log.Printf("🎉 [NIVEAUX] %s passe au niveau %d sur %s", name, level, guildID)
	}
	_ = h.DB.LogFeature(ctx, logEntry)
}

// guildLang turns the server's Discord locale (fr, en-US, pt-BR…) into a language of the bot's texts.
func guildLang(locale string) string {
	code, _, _ := strings.Cut(strings.ToLower(locale), "-")
	if _, ok := messages["levelup_default"][code]; ok {
		return code
	}
	return "en"
}

// discordError keeps the useful part of a Discord error for the journal ("Missing Permissions", "Unknown Channel").
func discordError(err error) string {
	if rest, ok := err.(*discordgo.RESTError); ok && rest.Message != nil {
		return rest.Message.Message
	}
	text := err.Error()
	if len(text) > 120 {
		text = text[:120]
	}
	return text
}

func escapeMarkdown(s string) string {
	return strings.NewReplacer("\\", "\\\\", "*", "\\*", "_", "\\_", "~", "\\~", "`", "\\`", "|", "\\|", ">", "\\>").Replace(s)
}
