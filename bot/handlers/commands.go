package handlers

import (
	"bytes"
	"context"
	"errors"
	"fmt"
	"log"
	"net/url"
	"strconv"
	"strings"
	"time"

	"hourglass-bot/card"

	"github.com/bwmarrin/discordgo"
)

var Commands = []*discordgo.ApplicationCommand{
	{
		Name:        "stats",
		Description: "Your voice and message stats on this server, as a card.",
		Options: []*discordgo.ApplicationCommandOption{
			{
				Type:        discordgo.ApplicationCommandOptionUser,
				Name:        "user",
				Description: "Target user (defaults to yourself)",
				Required:    false,
			},
		},
	},
	{
		Name:        "allstats",
		Description: "Your voice and message stats across every server, as a card.",
		Options: []*discordgo.ApplicationCommandOption{
			{
				Type:        discordgo.ApplicationCommandOptionUser,
				Name:        "user",
				Description: "Target user (defaults to yourself)",
				Required:    false,
			},
		},
	},
	{
		Name:        "versus",
		Description: "Head-to-head duel between two members, as a card.",
		Options: []*discordgo.ApplicationCommandOption{
			{
				Type:        discordgo.ApplicationCommandOptionUser,
				Name:        "player1",
				Description: "First member to compare",
				Required:    true,
			},
			{
				Type:        discordgo.ApplicationCommandOptionUser,
				Name:        "player2",
				Description: "Second member to compare",
				Required:    true,
			},
			{
				Type:        discordgo.ApplicationCommandOptionString,
				Name:        "scope",
				Description: "Compare on this server (default) or across every server",
				Required:    false,
				Choices: []*discordgo.ApplicationCommandOptionChoice{
					{Name: "This server", Value: "server"},
					{Name: "All servers", Value: "global"},
				},
			},
		},
	},
	{
		Name:        "server",
		Description: "Statistics of this server, as a card.",
	},
	{
		Name:        "top",
		Description: "Top 10 by voice time or messages, as a card.",
		Options: []*discordgo.ApplicationCommandOption{
			{
				Type:        discordgo.ApplicationCommandOptionString,
				Name:        "type",
				Description: "Ranking type (Voice or Messages)",
				Required:    false,
				Choices: []*discordgo.ApplicationCommandOptionChoice{
					{Name: "Voice", Value: "vocal"},
					{Name: "Messages", Value: "messages"},
				},
			},
			{
				Type:        discordgo.ApplicationCommandOptionString,
				Name:        "period",
				Description: "Time period filter",
				Required:    false,
				Choices: []*discordgo.ApplicationCommandOptionChoice{
					{Name: "All-Time", Value: "all"},
					{Name: "Last 30 Days", Value: "month"},
					{Name: "Last 7 Days", Value: "week"},
				},
			},
			{
				Type:        discordgo.ApplicationCommandOptionString,
				Name:        "scope",
				Description: "Leaderboard scope",
				Required:    false,
				Choices: []*discordgo.ApplicationCommandOptionChoice{
					{Name: "This Server", Value: "server"},
					{Name: "Global (All Servers)", Value: "global"},
				},
			},
		},
	},
	{
		Name:        "alltop",
		Description: "Top 10 across every server, as a card.",
	},
	{
		Name:        "help",
		Description: "Every Hourglass command.",
	},
}

func (h *BotHandler) RegisterSlashCommands(s *discordgo.Session) {
	_, err := s.ApplicationCommandBulkOverwrite(s.State.User.ID, "", Commands)
	if err != nil {
		log.Printf("ApplicationCommandBulkOverwrite failed: %v, falling back to individual registration...", err)
		for _, cmd := range Commands {
			_, errCreate := s.ApplicationCommandCreate(s.State.User.ID, "", cmd)
			if errCreate != nil {
				log.Printf("Failed to register command /%s: %v", cmd.Name, errCreate)
			}
		}
	} else {
		log.Printf("✅ %d slash commands synchronized with Discord (BulkOverwrite).", len(Commands))
	}
}

func (h *BotHandler) OnInteractionCreate(s *discordgo.Session, i *discordgo.InteractionCreate) {
	if i.Type != discordgo.InteractionApplicationCommand {
		return
	}

	started := time.Now()
	success := true
	note := ""
	// A panic in a command handler must never take the whole bot (and voice tracking) down.
	// Every command is then recorded for the website admin page (without any member identifier).
	defer func() {
		if r := recover(); r != nil {
			success = false
			log.Printf("❌ Panic in /%s command handler: %v", i.ApplicationCommandData().Name, r)
		}
		h.recordCommand(i, note, success, time.Since(started))
	}()

	data := i.ApplicationCommandData()

	// Server-scoped commands cannot run in DMs (no guild, no member)
	if i.GuildID == "" && (data.Name == "stats" || data.Name == "server") {
		note = "dm_refused"
		_ = s.InteractionRespond(i.Interaction, &discordgo.InteractionResponse{
			Type: discordgo.InteractionResponseChannelMessageWithSource,
			Data: &discordgo.InteractionResponseData{
				Content: "This command can only be used inside a server. Try `/allstats` or `/alltop` here.",
				Flags:   discordgo.MessageFlagsEphemeral,
			},
		})
		return
	}

	// Immediate deferral to guarantee response within Discord's 3-second deadline
	_ = s.InteractionRespond(i.Interaction, &discordgo.InteractionResponse{
		Type: discordgo.InteractionResponseDeferredChannelMessageWithSource,
	})

	ctx, cancel := context.WithTimeout(context.Background(), 15*time.Second)
	defer cancel()

	switch data.Name {
	case "stats":
		h.handleStats(ctx, s, i, false)
	case "allstats":
		h.handleStats(ctx, s, i, true)
	case "versus":
		h.handleVersus(ctx, s, i)
	case "server":
		h.handleServerStats(ctx, s, i)
	case "top":
		h.handleTopFiltered(ctx, s, i, false)
	case "alltop":
		h.handleTopFiltered(ctx, s, i, true)
	case "help":
		h.handleHelp(ctx, s, i)
	}
}

// sendCard posts a card drawn by the website with a short message; when the website cannot provide it
// (CARD_TOKEN missing, website down, no data) the command answers with text instead.
func sendCard(s *discordgo.Session, i *discordgo.InteractionCreate, png []byte, err error, fileName, content string, fallback func() string) {
	if err == nil && len(png) > 0 {
		_, _ = s.FollowupMessageCreate(i.Interaction, true, &discordgo.WebhookParams{
			Content: content,
			Files: []*discordgo.File{
				{Name: fileName, ContentType: "image/png", Reader: bytes.NewReader(png)},
			},
		})
		return
	}
	if err != nil && !errors.Is(err, card.ErrDisabled) && !errors.Is(err, card.ErrNotFound) {
		log.Printf("Card %s unavailable, answering with text: %v", fileName, err)
	}
	_, _ = s.FollowupMessageCreate(i.Interaction, true, &discordgo.WebhookParams{Content: fallback()})
}

// fallbackContext gives the text answer its own short deadline (the card request may have used the command's).
func fallbackContext() (context.Context, context.CancelFunc) {
	return context.WithTimeout(context.Background(), 5*time.Second)
}

// userTotals returns the voice time (ongoing sessions included) and messages of a member, on one server or everywhere.
func (h *BotHandler) userTotals(ctx context.Context, userID, serverID int64, global bool) (seconds, messages int64) {
	voice := `SELECT COALESCE(SUM(CASE WHEN left_at IS NOT NULL THEN duration_seconds
	          ELSE EXTRACT(EPOCH FROM (NOW() - joined_at))::INT END), 0) FROM voice_sessions WHERE user_id = $1`
	msgs := `SELECT COALESCE(SUM(count), 0) FROM message_events WHERE user_id = $1`
	if global {
		_ = h.DB.Pool.QueryRow(ctx, voice, userID).Scan(&seconds)
		_ = h.DB.Pool.QueryRow(ctx, msgs, userID).Scan(&messages)
	} else {
		_ = h.DB.Pool.QueryRow(ctx, voice+" AND server_id = $2", userID, serverID).Scan(&seconds)
		_ = h.DB.Pool.QueryRow(ctx, msgs+" AND server_id = $2", userID, serverID).Scan(&messages)
	}
	return
}

func (h *BotHandler) handleStats(ctx context.Context, s *discordgo.Session, i *discordgo.InteractionCreate, isGlobal bool) {
	// i.Member is only set in guilds; in DMs the invoker is in i.User
	targetUser := i.User
	if i.Member != nil {
		targetUser = i.Member.User
	}
	for _, opt := range i.ApplicationCommandData().Options {
		if opt.Name == "user" || opt.Name == "utilisateur" {
			targetUser = opt.UserValue(s)
		}
	}
	userID, _ := strconv.ParseInt(targetUser.ID, 10, 64)
	serverID, _ := strconv.ParseInt(i.GuildID, 10, 64)

	params := url.Values{"user": {targetUser.ID}}
	if !isGlobal {
		params.Set("server", i.GuildID)
	}
	png, err := card.Fetch(ctx, "member", params)
	link := fmt.Sprintf("[View full profile on hourglassbot.net](https://hourglassbot.net/profile/%d)", userID)

	sendCard(s, i, png, err, fmt.Sprintf("stats_%d.png", userID), link, func() string {
		if errors.Is(err, card.ErrNotFound) {
			return fmt.Sprintf("Hourglass has no activity recorded for **%s** yet.", targetUser.Username)
		}
		fctx, cancel := fallbackContext()
		defer cancel()
		seconds, messages := h.userTotals(fctx, userID, serverID, isGlobal)
		scope := "on this server"
		if isGlobal {
			scope = "on all servers"
		}
		return fmt.Sprintf("**%s** %s\n• Voice time: **%s**\n• Messages: **%s**\n%s",
			targetUser.Username, scope, card.FormatDuration(seconds), card.FormatNumber(messages), link)
	})
}

func (h *BotHandler) handleVersus(ctx context.Context, s *discordgo.Session, i *discordgo.InteractionCreate) {
	var u1, u2 *discordgo.User
	scope := "server"
	for _, opt := range i.ApplicationCommandData().Options {
		switch opt.Name {
		case "player1", "joueur1":
			u1 = opt.UserValue(s)
		case "player2", "joueur2":
			u2 = opt.UserValue(s)
		case "scope", "portee":
			scope = opt.StringValue()
		}
	}
	if u1 == nil || u2 == nil {
		_, _ = s.FollowupMessageCreate(i.Interaction, true, &discordgo.WebhookParams{
			Content: "Please designate two valid members for the duel.",
		})
		return
	}
	isGlobal := scope == "global" || i.GuildID == ""
	u1ID, _ := strconv.ParseInt(u1.ID, 10, 64)
	u2ID, _ := strconv.ParseInt(u2.ID, 10, 64)
	serverID, _ := strconv.ParseInt(i.GuildID, 10, 64)

	params := url.Values{"u1": {u1.ID}, "u2": {u2.ID}}
	link := fmt.Sprintf("[Full comparison on hourglassbot.net](https://hourglassbot.net/versus?u1=%d&u2=%d)", u1ID, u2ID)
	if !isGlobal {
		params.Set("server", i.GuildID)
		link = fmt.Sprintf("[Full comparison on hourglassbot.net](https://hourglassbot.net/versus?u1=%d&u2=%d&srv=%d)", u1ID, u2ID, serverID)
	}
	png, err := card.Fetch(ctx, "versus", params)

	sendCard(s, i, png, err, fmt.Sprintf("versus_%d_%d.png", u1ID, u2ID), link, func() string {
		if errors.Is(err, card.ErrNotFound) {
			return "Hourglass has no activity recorded for one of these members yet."
		}
		fctx, cancel := fallbackContext()
		defer cancel()
		s1, m1 := h.userTotals(fctx, u1ID, serverID, isGlobal)
		s2, m2 := h.userTotals(fctx, u2ID, serverID, isGlobal)
		return fmt.Sprintf("**%s VS %s**\n• **%s**: %s voice · %s messages\n• **%s**: %s voice · %s messages\n%s",
			u1.Username, u2.Username,
			u1.Username, card.FormatDuration(s1), card.FormatNumber(m1),
			u2.Username, card.FormatDuration(s2), card.FormatNumber(m2), link)
	})
}

func (h *BotHandler) handleServerStats(ctx context.Context, s *discordgo.Session, i *discordgo.InteractionCreate) {
	serverID, _ := strconv.ParseInt(i.GuildID, 10, 64)
	png, err := card.Fetch(ctx, "server", url.Values{"server": {i.GuildID}})
	link := fmt.Sprintf("[Server dashboard on hourglassbot.net](https://hourglassbot.net/server/%d)", serverID)

	sendCard(s, i, png, err, fmt.Sprintf("server_%d.png", serverID), link, func() string {
		if errors.Is(err, card.ErrNotFound) {
			return "Hourglass has no activity recorded for this server yet."
		}
		fctx, cancel := fallbackContext()
		defer cancel()
		var seconds, messages int64
		_ = h.DB.Pool.QueryRow(fctx, `SELECT COALESCE(SUM(CASE WHEN left_at IS NOT NULL THEN duration_seconds
			ELSE EXTRACT(EPOCH FROM (NOW() - joined_at))::INT END), 0) FROM voice_sessions WHERE server_id = $1`, serverID).Scan(&seconds)
		_ = h.DB.Pool.QueryRow(fctx, `SELECT COALESCE(SUM(count), 0) FROM message_events WHERE server_id = $1`, serverID).Scan(&messages)
		name := "this server"
		if guild, gerr := s.State.Guild(i.GuildID); gerr == nil && guild != nil {
			name = guild.Name
		}
		return fmt.Sprintf("**%s**\n• Voice time: **%s**\n• Messages: **%s**\n%s",
			name, card.FormatDuration(seconds), card.FormatNumber(messages), link)
	})
}

func (h *BotHandler) handleTopFiltered(ctx context.Context, s *discordgo.Session, i *discordgo.InteractionCreate, forceGlobal bool) {
	rankingType := "vocal"
	period := "all"
	scope := "server"
	for _, opt := range i.ApplicationCommandData().Options {
		switch opt.Name {
		case "type":
			rankingType = opt.StringValue()
		case "period", "periode":
			period = opt.StringValue()
		case "scope", "portee":
			scope = opt.StringValue()
		}
	}
	isGlobal := forceGlobal || scope == "global" || i.GuildID == ""
	serverID, _ := strconv.ParseInt(i.GuildID, 10, 64)

	webType := "voice"
	if rankingType == "messages" {
		webType = "messages"
	}
	params := url.Values{"type": {webType}, "period": {period}}
	link := "[Full leaderboard on hourglassbot.net](https://hourglassbot.net/members)"
	if !isGlobal {
		params.Set("server", i.GuildID)
		link = fmt.Sprintf("[Full leaderboard on hourglassbot.net](https://hourglassbot.net/members?server_id=%d)", serverID)
	}
	png, err := card.Fetch(ctx, "top", params)

	sendCard(s, i, png, err, fmt.Sprintf("top_%s_%s.png", webType, period), link, func() string {
		fctx, cancel := fallbackContext()
		defer cancel()
		return h.topText(fctx, rankingType, period, isGlobal, serverID) + "\n" + link
	})
}

// topText is the text leaderboard used when the card cannot be drawn.
func (h *BotHandler) topText(ctx context.Context, rankingType, period string, isGlobal bool, serverID int64) string {
	interval := ""
	switch period {
	case "week":
		interval = "7 days"
	case "month":
		interval = "30 days"
	}
	var query string
	if rankingType == "messages" {
		query = `SELECT COALESCE(u.username, 'Member'), SUM(m.count) AS total_val
			FROM message_events m LEFT JOIN users u ON u.user_id = m.user_id WHERE TRUE`
		if interval != "" {
			query += " AND m.created_at >= NOW() - INTERVAL '" + interval + "'"
		}
		if !isGlobal {
			query += " AND m.server_id = $1"
		}
		query += " GROUP BY m.user_id, u.username ORDER BY total_val DESC LIMIT 10"
	} else {
		query = `SELECT COALESCE(u.username, 'Member'),
			SUM(CASE WHEN vs.left_at IS NOT NULL THEN vs.duration_seconds ELSE EXTRACT(EPOCH FROM (NOW() - vs.joined_at))::INT END) AS total_val
			FROM voice_sessions vs LEFT JOIN users u ON u.user_id = vs.user_id WHERE TRUE`
		if interval != "" {
			query += " AND vs.joined_at >= NOW() - INTERVAL '" + interval + "'"
		}
		if !isGlobal {
			query += " AND vs.server_id = $1"
		}
		query += " GROUP BY vs.user_id, u.username ORDER BY total_val DESC LIMIT 10"
	}
	var args []interface{}
	if !isGlobal {
		args = append(args, serverID)
	}
	rows, err := h.DB.Pool.Query(ctx, query, args...)
	if err != nil {
		log.Printf("Error querying the text leaderboard: %v", err)
		return "The leaderboard is unavailable right now."
	}
	defer rows.Close()

	title := "Voice"
	if rankingType == "messages" {
		title = "Messages"
	}
	out := fmt.Sprintf("**Top 10 · %s**\n", title)
	rank := 0
	for rows.Next() {
		var username string
		var value int64
		if rows.Scan(&username, &value) != nil {
			continue
		}
		rank++
		valueStr := card.FormatDuration(value)
		if rankingType == "messages" {
			valueStr = card.FormatNumber(value)
		}
		out += fmt.Sprintf("%d. %s — %s\n", rank, username, valueStr)
	}
	if rank == 0 {
		return "No activity recorded for this period yet."
	}
	return out
}

func (h *BotHandler) handleHelp(ctx context.Context, s *discordgo.Session, i *discordgo.InteractionCreate) {
	commands := []struct{ name, desc string }{
		{"/stats [user]", "Your stats on this server: voice, messages, rank and showcase badges."},
		{"/allstats [user]", "Your stats across every server Hourglass tracks."},
		{"/top [type] [period] [scope]", "Top 10 by voice time or messages: all time, 30 days or 7 days."},
		{"/alltop", "Top 10 across every server."},
		{"/versus <player1> <player2> [scope]", "Head-to-head duel between two members, on this server or everywhere."},
		{"/server", "Statistics of this server: voice, messages, members and the last 30 days."},
		{"/help", "This list."},
	}
	var desc strings.Builder
	for _, c := range commands {
		desc.WriteString(fmt.Sprintf("`%s`\n%s\n\n", c.name, c.desc))
	}
	desc.WriteString("Cards use the color, banner and badges members choose on their profile at **[hourglassbot.net](https://hourglassbot.net)**.")

	_, _ = s.FollowupMessageCreate(i.Interaction, true, &discordgo.WebhookParams{
		Embeds: []*discordgo.MessageEmbed{{
			Title:       "Hourglass commands",
			URL:         "https://hourglassbot.net",
			Description: desc.String(),
			Color:       0x38bdf8,
			Footer:      &discordgo.MessageEmbedFooter{Text: "Voice and message activity · no audio and no message content recorded"},
		}},
	})
}

// recordCommand stores the command, its server and its choice options (type, period, scope) in the
// background: user options (mentions) are never stored, and a slow database never delays the reply.
func (h *BotHandler) recordCommand(i *discordgo.InteractionCreate, note string, success bool, duration time.Duration) {
	data := i.ApplicationCommandData()
	var parts []string
	for _, opt := range data.Options {
		if opt.Type == discordgo.ApplicationCommandOptionString {
			parts = append(parts, opt.Name+"="+opt.StringValue())
		}
	}
	if note != "" {
		parts = append(parts, note)
	}
	var serverID *int64
	if id, err := strconv.ParseInt(i.GuildID, 10, 64); err == nil {
		serverID = &id
	}
	command, options := data.Name, strings.Join(parts, " ")
	go func() {
		ctx, cancel := context.WithTimeout(context.Background(), 3*time.Second)
		defer cancel()
		if err := h.DB.RecordCommand(ctx, command, serverID, options, success, duration); err != nil {
			log.Printf("⚠️ Impossible d'enregistrer la commande /%s: %v", command, err)
		}
	}()
}
