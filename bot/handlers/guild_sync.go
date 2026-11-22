package handlers

import (
	"context"
	"log"
	"sort"
	"strconv"
	"sync"
	"time"

	"hourglass-bot/database"

	"github.com/bwmarrin/discordgo"
)

// Copy of each server for the website (server management page): owner, language, the bot's permissions, text
// channels, roles and members. Written when the bot arrives on a server, after each change Discord reports
// (debounced: one write a few seconds after a burst of changes), and again every 15 minutes as a safety net.

const (
	guildSyncDelay   = 3 * time.Second  // waits for a burst of changes (a channel created with its permissions…)
	memberSyncDelay  = 5 * time.Second  // waits for the last pieces of a member list
	guildSyncPeriod  = 15 * time.Minute // full copy again, in case an event was missed
	guildSyncTimeout = 20 * time.Second
)

// Rights never given by an automatic role: administration and moderation
const dangerousPermissions = discordgo.PermissionAdministrator |
	discordgo.PermissionManageGuild |
	discordgo.PermissionManageRoles |
	discordgo.PermissionManageChannels |
	discordgo.PermissionBanMembers |
	discordgo.PermissionKickMembers |
	discordgo.PermissionModerateMembers |
	discordgo.PermissionManageMessages |
	discordgo.PermissionMentionEveryone |
	discordgo.PermissionManageWebhooks |
	discordgo.PermissionManageNicknames |
	discordgo.PermissionManageGuildExpressions |
	discordgo.PermissionManageThreads |
	discordgo.PermissionViewAuditLogs

type guildSyncer struct {
	mu          sync.Mutex
	stateTimers map[string]*time.Timer
	memberTimer map[string]*time.Timer
	loopOnce    sync.Once
	readyAt     time.Time // last READY: servers created long after it were joined while running
}

var syncer = &guildSyncer{stateTimers: map[string]*time.Timer{}, memberTimer: map[string]*time.Timer{}}

func (g *guildSyncer) schedule(timers map[string]*time.Timer, guildID string, delay time.Duration, run func()) {
	g.mu.Lock()
	defer g.mu.Unlock()
	if t, ok := timers[guildID]; ok {
		t.Stop()
	}
	timers[guildID] = time.AfterFunc(delay, func() {
		g.mu.Lock()
		delete(timers, guildID)
		g.mu.Unlock()
		run()
	})
}

// scheduleGuildSync writes the meta, channels and roles of a server a few seconds from now.
func (h *BotHandler) scheduleGuildSync(s *discordgo.Session, guildID string) {
	if guildID == "" {
		return
	}
	syncer.schedule(syncer.stateTimers, guildID, guildSyncDelay, func() { h.syncGuildState(s, guildID) })
}

// scheduleMemberSync writes the member list of a server a few seconds from now.
func (h *BotHandler) scheduleMemberSync(s *discordgo.Session, guildID string) {
	if guildID == "" {
		return
	}
	syncer.schedule(syncer.memberTimer, guildID, memberSyncDelay, func() { h.syncGuildMembers(s, guildID) })
}

// startGuildSyncLoop copies every server again every 15 minutes (started once, whatever the reconnections).
func (h *BotHandler) startGuildSyncLoop(s *discordgo.Session) {
	syncer.loopOnce.Do(func() {
		go func() {
			ticker := time.NewTicker(guildSyncPeriod)
			defer ticker.Stop()
			for range ticker.C {
				for _, g := range s.State.Guilds {
					h.syncGuildState(s, g.ID)
					h.syncGuildMembers(s, g.ID)
				}
			}
		}()
	})
}

// guildPermissions computes the server-wide permissions of a member (everyone role + their roles; all of them for
// the owner or an administrator).
func guildPermissions(guild *discordgo.Guild, userID string, roleIDs []string) int64 {
	if userID == guild.OwnerID {
		return discordgo.PermissionAll
	}
	var perms int64
	has := make(map[string]bool, len(roleIDs))
	for _, id := range roleIDs {
		has[id] = true
	}
	for _, r := range guild.Roles {
		if r.ID == guild.ID || has[r.ID] {
			perms |= r.Permissions
		}
	}
	if perms&discordgo.PermissionAdministrator != 0 {
		perms |= discordgo.PermissionAll
	}
	return perms
}

func (h *BotHandler) syncGuildState(s *discordgo.Session, guildID string) {
	guild, err := s.State.Guild(guildID)
	if err != nil || guild == nil || guild.Unavailable || s.State.User == nil {
		return
	}
	serverID, err := strconv.ParseInt(guild.ID, 10, 64)
	if err != nil {
		return
	}
	botID := s.State.User.ID
	var botRoles []string
	if me, err := s.State.Member(guild.ID, botID); err == nil && me != nil {
		botRoles = me.Roles
	}
	botPerms := guildPermissions(guild, botID, botRoles)

	// The bot's highest role: it can only give the roles under it
	topPosition := 0
	position := make(map[string]int, len(guild.Roles))
	for _, r := range guild.Roles {
		position[r.ID] = r.Position
	}
	for _, id := range botRoles {
		if p := position[id]; p > topPosition {
			topPosition = p
		}
	}

	owner, _ := strconv.ParseInt(guild.OwnerID, 10, 64)
	meta := database.GuildMeta{
		ServerID: serverID, OwnerID: owner, Locale: string(guild.PreferredLocale),
		BotPermissions: botPerms, BotTopRolePosition: topPosition, MemberCount: guild.MemberCount,
	}

	categories := make(map[string]string)
	for _, c := range guild.Channels {
		if c.Type == discordgo.ChannelTypeGuildCategory {
			categories[c.ID] = c.Name
		}
	}
	channels := make([]database.GuildChannel, 0, len(guild.Channels))
	for _, c := range guild.Channels {
		kind := ""
		switch c.Type {
		case discordgo.ChannelTypeGuildText:
			kind = "text"
		case discordgo.ChannelTypeGuildNews:
			kind = "announcement"
		default:
			continue
		}
		id, err := strconv.ParseInt(c.ID, 10, 64)
		if err != nil {
			continue
		}
		perms, err := s.State.UserChannelPermissions(botID, c.ID)
		if err != nil {
			perms = 0
		}
		view := perms&discordgo.PermissionViewChannel != 0
		channels = append(channels, database.GuildChannel{
			ChannelID: id, Name: c.Name, Kind: kind, Category: categories[c.ParentID], Position: c.Position,
			CanView:   view,
			CanSend:   view && perms&discordgo.PermissionSendMessages != 0,
			CanEmbed:  view && perms&discordgo.PermissionEmbedLinks != 0,
			CanAttach: view && perms&discordgo.PermissionAttachFiles != 0,
		})
	}
	sort.Slice(channels, func(i, j int) bool { return channels[i].Position < channels[j].Position })

	canManageRoles := botPerms&discordgo.PermissionManageRoles != 0
	roles := make([]database.GuildRole, 0, len(guild.Roles))
	for _, r := range guild.Roles {
		id, err := strconv.ParseInt(r.ID, 10, 64)
		if err != nil || r.ID == guild.ID { // @everyone is nobody's to give
			continue
		}
		dangerous := r.Permissions&dangerousPermissions != 0
		roles = append(roles, database.GuildRole{
			RoleID: id, Name: r.Name, Color: r.Color, Position: r.Position, Managed: r.Managed, Permissions: r.Permissions,
			Assignable: canManageRoles && !r.Managed && r.Position < topPosition,
			Dangerous:  dangerous,
		})
	}

	ctx, cancel := context.WithTimeout(context.Background(), guildSyncTimeout)
	defer cancel()
	if err := h.DB.SaveGuildState(ctx, meta, channels, roles); err != nil {
		log.Printf("⚠️ [GESTION] Copie du serveur %s impossible: %v", guild.ID, err)
	}
}

func memberRow(m *discordgo.Member) (database.GuildMember, bool) {
	if m == nil || m.User == nil || m.User.Bot {
		return database.GuildMember{}, false
	}
	id, err := strconv.ParseInt(m.User.ID, 10, 64)
	if err != nil {
		return database.GuildMember{}, false
	}
	display := m.Nick
	if display == "" {
		display = m.User.GlobalName
	}
	if display == "" {
		display = m.User.Username
	}
	row := database.GuildMember{UserID: id, Username: m.User.Username, DisplayName: display, Avatar: m.AvatarURL("128")}
	if !m.JoinedAt.IsZero() {
		joined := m.JoinedAt.UTC()
		row.JoinedAt = &joined
	}
	return row, true
}

func (h *BotHandler) syncGuildMembers(s *discordgo.Session, guildID string) {
	guild, err := s.State.Guild(guildID)
	if err != nil || guild == nil || guild.Unavailable {
		return
	}
	serverID, err := strconv.ParseInt(guild.ID, 10, 64)
	if err != nil {
		return
	}
	// A partial list (still arriving) would remove real members: wait for most of it
	if len(guild.Members) == 0 || (guild.MemberCount > 0 && len(guild.Members) < guild.MemberCount*9/10) {
		return
	}
	rows := make([]database.GuildMember, 0, len(guild.Members))
	for _, m := range guild.Members {
		if row, ok := memberRow(m); ok {
			rows = append(rows, row)
		}
	}
	ctx, cancel := context.WithTimeout(context.Background(), guildSyncTimeout)
	defer cancel()
	if err := h.DB.ReplaceGuildMembers(ctx, serverID, rows); err != nil {
		log.Printf("⚠️ [GESTION] Liste des membres du serveur %s non enregistrée: %v", guild.ID, err)
	}
}

// --------------------------------------------------------------------------- Discord events

// OnGuildMembersChunk: the member list of a server arrives in pieces; written once the last one is in.
func (h *BotHandler) OnGuildMembersChunk(s *discordgo.Session, c *discordgo.GuildMembersChunk) {
	if c.ChunkIndex == c.ChunkCount-1 {
		h.scheduleMemberSync(s, c.GuildID)
	}
}

func (h *BotHandler) OnGuildMemberAdd(s *discordgo.Session, m *discordgo.GuildMemberAdd) {
	if row, ok := memberRow(m.Member); ok {
		serverID, _ := strconv.ParseInt(m.GuildID, 10, 64)
		ctx, cancel := context.WithTimeout(context.Background(), 3*time.Second)
		defer cancel()
		_ = h.DB.UpsertGuildMember(ctx, serverID, row)
		// Automatic roles: a newcomer is checked at the next minute (tiers without condition)
		if userID, err := strconv.ParseInt(m.User.ID, 10, 64); err == nil && !m.User.Bot {
			markRoleActivity(serverID, userID)
		}
	}
}

func (h *BotHandler) OnGuildMemberRemove(s *discordgo.Session, m *discordgo.GuildMemberRemove) {
	if m.Member == nil || m.Member.User == nil {
		return
	}
	serverID, _ := strconv.ParseInt(m.GuildID, 10, 64)
	userID, err := strconv.ParseInt(m.Member.User.ID, 10, 64)
	if err != nil {
		return
	}
	ctx, cancel := context.WithTimeout(context.Background(), 3*time.Second)
	defer cancel()
	_ = h.DB.DeleteGuildMember(ctx, serverID, userID)
}

func (h *BotHandler) OnGuildMemberUpdate(s *discordgo.Session, m *discordgo.GuildMemberUpdate) {
	if m.Member == nil || m.Member.User == nil {
		return
	}
	// The bot's own roles changed: its permissions and the roles it can give changed with them
	if s.State.User != nil && m.Member.User.ID == s.State.User.ID {
		h.scheduleGuildSync(s, m.GuildID)
		return
	}
	if row, ok := memberRow(m.Member); ok {
		serverID, _ := strconv.ParseInt(m.GuildID, 10, 64)
		ctx, cancel := context.WithTimeout(context.Background(), 3*time.Second)
		defer cancel()
		_ = h.DB.UpsertGuildMember(ctx, serverID, row)
	}
}

// Owner, language, channels and roles: written again after any change
func (h *BotHandler) OnGuildUpdate(s *discordgo.Session, g *discordgo.GuildUpdate) {
	if g.Guild != nil {
		h.scheduleGuildSync(s, g.ID)
	}
}

func (h *BotHandler) OnChannelCreate(s *discordgo.Session, c *discordgo.ChannelCreate) {
	if c.Channel != nil {
		h.scheduleGuildSync(s, c.GuildID)
	}
}

func (h *BotHandler) OnChannelUpdate(s *discordgo.Session, c *discordgo.ChannelUpdate) {
	if c.Channel != nil {
		h.scheduleGuildSync(s, c.GuildID)
	}
}

func (h *BotHandler) OnChannelDelete(s *discordgo.Session, c *discordgo.ChannelDelete) {
	if c.Channel != nil {
		h.scheduleGuildSync(s, c.GuildID)
	}
}

func (h *BotHandler) OnGuildRoleCreate(s *discordgo.Session, r *discordgo.GuildRoleCreate) {
	h.scheduleGuildSync(s, r.GuildID)
}

func (h *BotHandler) OnGuildRoleUpdate(s *discordgo.Session, r *discordgo.GuildRoleUpdate) {
	h.scheduleGuildSync(s, r.GuildID)
}

func (h *BotHandler) OnGuildRoleDelete(s *discordgo.Session, r *discordgo.GuildRoleDelete) {
	h.scheduleGuildSync(s, r.GuildID)
}
