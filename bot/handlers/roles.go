package handlers

import (
	"context"
	"fmt"
	"log"
	"strconv"
	"sync"
	"time"

	"hourglass-bot/database"

	"github.com/bwmarrin/discordgo"
)

// Automatic roles (website, server management > Roles): roles given and removed by themselves according to the
// activity of each member on the server (voice hours, messages, level; in total or over the last 30 days).
//
//   - A member is checked within a minute when they write or are in voice, and every member of the server once an
//     hour (criteria over 30 days go down by themselves) and right after the rules change.
//   - The bot only removes the roles it gave itself (role_grants): a role given by hand is never touched. Deleting a
//     rule or turning the feature off removes nothing.
//   - The Administrator role, managed roles and roles above the bot are never given, whatever the database says
//     (checked again before each change). Moderation roles may be given: the website warns about them.
//   - Changes go through one queue, one at a time: turning it on for a big server spreads hundreds of roles over a
//     few minutes instead of hitting Discord's limits.

const (
	rolesTick         = time.Minute
	rolesFullPeriod   = time.Hour
	rolesActionGap    = 300 * time.Millisecond
	rolesQueueSize    = 20000
	rolesPauseOnError = time.Hour     // Discord refused (permissions): that server's changes wait
	rolesWarnEvery    = 6 * time.Hour // a blocked role is written to the journal at most this often
	rolesTimeout      = 30 * time.Second
	rolesAuditReason  = "Hourglass: automatic role"
)

// --------------------------------------------------------------------------- rules (pure, tested)

func conditionMet(c database.RoleCondition, m database.MemberMetrics) bool {
	switch c.Metric {
	case "voice":
		seconds := m.VoiceTotal
		if c.Scope == "30d" {
			seconds = m.Voice30d
		}
		return float64(seconds)/3600 >= c.Min
	case "messages":
		n := m.MessagesAll
		if c.Scope == "30d" {
			n = m.Messages30d
		}
		return float64(n) >= c.Min
	case "level":
		return float64(levelFor(m.VoiceTotal, m.MessagesAll)) >= c.Min
	}
	return false
}

func ruleMet(r database.RoleRule, m database.MemberMetrics) bool {
	// A tier without condition (website 3.52.0) is met by every member, from the moment they join
	if len(r.Conditions) == 0 {
		return true
	}
	anyOf := r.Match == "any"
	for _, c := range r.Conditions {
		met := conditionMet(c, m)
		if anyOf && met {
			return true
		}
		if !anyOf && !met {
			return false
		}
	}
	return !anyOf
}

// rolePlan is what to do for one member: roles to give, to remove, and grants to forget (the role is already gone).
type rolePlan struct {
	Add, Remove, Forget []int64
}

// planMember compares what the rules want with the member's roles (has) and the roles the bot gave them (granted).
//   - wanted: in each rule, the roles of the tiers met, or only the last tier met when the rule keeps the highest;
//     a role wanted by any rule is wanted;
//   - a wanted role the member lacks is given;
//   - a role no longer wanted is removed only when the bot gave it, and only when RemoveUnmet is set or when a
//     higher tier replaces it (its own tier still met);
//   - a grant whose role the member no longer has (removed by hand) is forgotten.
func planMember(settings *database.RoleSettings, m database.MemberMetrics, has, granted map[int64]bool) rolePlan {
	var order []int64 // each role once, in the order of the page
	seen := map[int64]bool{}
	met := map[int64]bool{}
	wanted := map[int64]bool{}
	for _, ladder := range settings.Ladders {
		var highest int64
		for _, t := range ladder.Tiers {
			if !seen[t.RoleID] {
				seen[t.RoleID] = true
				order = append(order, t.RoleID)
			}
			if ruleMet(t, m) {
				met[t.RoleID] = true
				highest = t.RoleID
				if !ladder.KeepHighest {
					wanted[t.RoleID] = true
				}
			}
		}
		if ladder.KeepHighest && highest != 0 {
			wanted[highest] = true
		}
	}
	var plan rolePlan
	for _, role := range order {
		switch {
		case wanted[role] && !has[role]:
			plan.Add = append(plan.Add, role)
		case !wanted[role] && has[role] && granted[role] && (settings.RemoveUnmet || met[role]):
			plan.Remove = append(plan.Remove, role)
		case !wanted[role] && !has[role] && granted[role]:
			plan.Forget = append(plan.Forget, role)
		}
	}
	return plan
}

// --------------------------------------------------------------------------- manager

type roleAction struct {
	ServerID, UserID, RoleID int64
	Add                      bool
}

func (a roleAction) key() string {
	return fmt.Sprintf("%d:%d:%d:%t", a.ServerID, a.UserID, a.RoleID, a.Add)
}

type rolesManager struct {
	mu       sync.Mutex
	settings map[int64]*database.RoleSettings
	lastFull map[int64]time.Time
	version  map[int64]time.Time // rules' updated_at at the last full pass
	dirty    map[int64]map[int64]bool
	pending  map[string]bool
	paused   map[int64]time.Time // server -> changes paused until
	warned   map[string]time.Time
	queue    chan roleAction
	once     sync.Once
}

var autoRoles = &rolesManager{
	settings: map[int64]*database.RoleSettings{}, lastFull: map[int64]time.Time{}, version: map[int64]time.Time{},
	dirty: map[int64]map[int64]bool{}, pending: map[string]bool{}, paused: map[int64]time.Time{}, warned: map[string]time.Time{},
	queue: make(chan roleAction, rolesQueueSize),
}

// startRoles loads the rules now and every minute, and runs the queue (started once, whatever the reconnections).
func (h *BotHandler) startRoles(s *discordgo.Session) {
	autoRoles.once.Do(func() {
		go h.runRoleQueue(s)
		go func() {
			ticker := time.NewTicker(rolesTick)
			defer ticker.Stop()
			for {
				h.runRoleChecks(s)
				<-ticker.C
			}
		}()
	})
}

// markRoleActivity: the member just wrote on this server, checked at the next minute.
func markRoleActivity(serverID, userID int64) {
	autoRoles.mu.Lock()
	defer autoRoles.mu.Unlock()
	if _, ok := autoRoles.settings[serverID]; !ok {
		return
	}
	if autoRoles.dirty[serverID] == nil {
		autoRoles.dirty[serverID] = map[int64]bool{}
	}
	autoRoles.dirty[serverID][userID] = true
}

func (h *BotHandler) runRoleChecks(s *discordgo.Session) {
	ctx, cancel := context.WithTimeout(context.Background(), 20*time.Second)
	settings, err := h.DB.LoadRoleSettings(ctx)
	cancel()
	if err != nil {
		log.Printf("⚠️ [RÔLES] Règles illisibles: %v", err)
		return
	}
	now := time.Now()
	autoRoles.mu.Lock()
	autoRoles.settings = settings
	type job struct {
		settings *database.RoleSettings
		full     bool
		users    []int64
	}
	jobs := make([]job, 0, len(settings))
	for id, st := range settings {
		full := now.Sub(autoRoles.lastFull[id]) >= rolesFullPeriod || !autoRoles.version[id].Equal(st.UpdatedAt)
		j := job{settings: st, full: full}
		if full {
			autoRoles.lastFull[id], autoRoles.version[id] = now, st.UpdatedAt
		} else {
			for u := range autoRoles.dirty[id] {
				j.users = append(j.users, u)
			}
		}
		jobs = append(jobs, j)
	}
	autoRoles.dirty = map[int64]map[int64]bool{}
	for k, t := range autoRoles.warned {
		if now.Sub(t) > rolesWarnEvery {
			delete(autoRoles.warned, k)
		}
	}
	autoRoles.mu.Unlock()

	for _, j := range jobs {
		if len(j.settings.Ladders) == 0 {
			continue
		}
		if j.full {
			h.checkRoleMembers(s, j.settings, 0)
			continue
		}
		// Members in voice right now: their hours go up without any message
		seen := map[int64]bool{}
		users := j.users
		if guild, err := s.State.Guild(strconv.FormatInt(j.settings.ServerID, 10)); err == nil && guild != nil {
			s.State.RLock()
			for _, vs := range guild.VoiceStates {
				if vs.ChannelID == "" {
					continue
				}
				if id, err := strconv.ParseInt(vs.UserID, 10, 64); err == nil {
					users = append(users, id)
				}
			}
			s.State.RUnlock()
		}
		for _, u := range users {
			if !seen[u] {
				seen[u] = true
				h.checkRoleMembers(s, j.settings, u)
			}
		}
	}
}

// checkRoleMembers checks every member of the server (userID 0) or one member, and queues the changes.
func (h *BotHandler) checkRoleMembers(s *discordgo.Session, settings *database.RoleSettings, userID int64) {
	ctx, cancel := context.WithTimeout(context.Background(), rolesTimeout)
	defer cancel()
	metrics, err := h.DB.ServerMemberMetrics(ctx, settings.ServerID, userID)
	if err != nil {
		log.Printf("⚠️ [RÔLES] Activité des membres de %d illisible: %v", settings.ServerID, err)
		return
	}
	grants, err := h.DB.RoleGrants(ctx, settings.ServerID, userID)
	if err != nil {
		return
	}
	guildID := strconv.FormatInt(settings.ServerID, 10)
	for uid, m := range metrics {
		member, err := s.State.Member(guildID, strconv.FormatInt(uid, 10))
		if err != nil || member == nil || member.User == nil || member.User.Bot {
			continue
		}
		has := make(map[int64]bool, len(member.Roles))
		s.State.RLock()
		for _, r := range member.Roles {
			if id, err := strconv.ParseInt(r, 10, 64); err == nil {
				has[id] = true
			}
		}
		s.State.RUnlock()
		plan := planMember(settings, m, has, grants[uid])
		for _, role := range plan.Forget {
			_ = h.DB.SetRoleGrant(ctx, settings.ServerID, uid, role, false)
		}
		for _, role := range plan.Add {
			enqueueRole(roleAction{ServerID: settings.ServerID, UserID: uid, RoleID: role, Add: true})
		}
		for _, role := range plan.Remove {
			enqueueRole(roleAction{ServerID: settings.ServerID, UserID: uid, RoleID: role, Add: false})
		}
	}
}

func enqueueRole(a roleAction) {
	autoRoles.mu.Lock()
	if autoRoles.pending[a.key()] || time.Now().Before(autoRoles.paused[a.ServerID]) {
		autoRoles.mu.Unlock()
		return
	}
	autoRoles.pending[a.key()] = true
	autoRoles.mu.Unlock()
	select {
	case autoRoles.queue <- a:
	default: // full: dropped for now, the next pass queues it again
		autoRoles.mu.Lock()
		delete(autoRoles.pending, a.key())
		autoRoles.mu.Unlock()
	}
}

// roleProblem tells why the bot must not give this role right now ("" when it may): checked on Discord's live
// state, never only on the database.
func roleProblem(s *discordgo.Session, guildID, roleID string) string {
	guild, err := s.State.Guild(guildID)
	if err != nil || guild == nil || s.State.User == nil {
		return "server unavailable"
	}
	if roleID == guildID {
		return "@everyone"
	}
	me, err := s.State.Member(guildID, s.State.User.ID)
	if err != nil || me == nil {
		return "bot member unknown"
	}
	s.State.RLock()
	defer s.State.RUnlock()
	var role *discordgo.Role
	position := map[string]int{}
	for _, r := range guild.Roles {
		position[r.ID] = r.Position
		if r.ID == roleID {
			role = r
		}
	}
	if role == nil {
		return "role deleted"
	}
	if role.Managed {
		return "managed role"
	}
	// Moderation roles may be given (the website warns in orange); the Administrator role never: any active member
	// would become a full admin of the server
	if role.Permissions&discordgo.PermissionAdministrator != 0 {
		return "administrator role"
	}
	if guildPermissions(guild, me.User.ID, me.Roles)&discordgo.PermissionManageRoles == 0 {
		return "Manage Roles missing"
	}
	top := 0
	for _, id := range me.Roles {
		if p := position[id]; p > top {
			top = p
		}
	}
	if role.Position >= top {
		return "role above the bot"
	}
	return ""
}

func (h *BotHandler) runRoleQueue(s *discordgo.Session) {
	for a := range autoRoles.queue {
		h.applyRole(s, a)
		autoRoles.mu.Lock()
		delete(autoRoles.pending, a.key())
		autoRoles.mu.Unlock()
		time.Sleep(rolesActionGap)
	}
}

func (h *BotHandler) applyRole(s *discordgo.Session, a roleAction) {
	autoRoles.mu.Lock()
	paused := time.Now().Before(autoRoles.paused[a.ServerID])
	autoRoles.mu.Unlock()
	if paused {
		return
	}
	ctx, cancel := context.WithTimeout(context.Background(), rolesTimeout)
	defer cancel()
	guildID, userID, roleID := strconv.FormatInt(a.ServerID, 10), strconv.FormatInt(a.UserID, 10), strconv.FormatInt(a.RoleID, 10)
	roleName := roleID
	if r, err := s.State.Role(guildID, roleID); err == nil && r != nil {
		roleName = r.Name
	}

	if problem := roleProblem(s, guildID, roleID); problem != "" {
		// Written once in a while, not for each member
		key := guildID + ":" + roleID
		autoRoles.mu.Lock()
		_, recent := autoRoles.warned[key]
		if !recent {
			autoRoles.warned[key] = time.Now()
		}
		autoRoles.mu.Unlock()
		if !recent {
			_ = h.DB.LogFeature(ctx, database.FeatureLog{ServerID: a.ServerID, Feature: "roles", Action: "role_blocked",
				TargetID: 0, OK: false, Detail: "@" + roleName + " · " + problem})
		}
		return
	}

	var err error
	action := "role_added"
	if a.Add {
		err = s.GuildMemberRoleAdd(guildID, userID, roleID, discordgo.WithContext(ctx), discordgo.WithAuditLogReason(rolesAuditReason))
	} else {
		action = "role_removed"
		err = s.GuildMemberRoleRemove(guildID, userID, roleID, discordgo.WithContext(ctx), discordgo.WithAuditLogReason(rolesAuditReason))
	}
	if err != nil {
		if rest, ok := err.(*discordgo.RESTError); ok && rest.Message != nil && rest.Message.Code == discordgo.ErrCodeUnknownMember {
			return // left the server meanwhile
		}
		if rest, ok := err.(*discordgo.RESTError); ok && rest.Response != nil && rest.Response.StatusCode == 403 {
			autoRoles.mu.Lock()
			autoRoles.paused[a.ServerID] = time.Now().Add(rolesPauseOnError)
			autoRoles.mu.Unlock()
		}
		log.Printf("⚠️ [RÔLES] %s de @%s impossible sur %s: %v", action, roleName, guildID, err)
		_ = h.DB.LogFeature(ctx, database.FeatureLog{ServerID: a.ServerID, Feature: "roles", Action: action, TargetID: a.UserID,
			OK: false, Detail: "@" + roleName + " · " + discordError(err)})
		return
	}
	_ = h.DB.SetRoleGrant(ctx, a.ServerID, a.UserID, a.RoleID, a.Add)
	_ = h.DB.LogFeature(ctx, database.FeatureLog{ServerID: a.ServerID, Feature: "roles", Action: action, TargetID: a.UserID,
		OK: true, Detail: "@" + roleName})
	if a.Add {
		log.Printf("🏷️ [RÔLES] @%s donné à %s sur %s", roleName, userID, guildID)
	} else {
		log.Printf("🏷️ [RÔLES] @%s retiré à %s sur %s", roleName, userID, guildID)
	}
}
