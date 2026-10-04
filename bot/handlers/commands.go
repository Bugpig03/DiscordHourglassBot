package handlers

import (
	"bytes"
	"context"
	"fmt"
	"log"
	"strconv"
	"time"

	"hourglass-bot/card"

	"github.com/bwmarrin/discordgo"
)

var Commands = []*discordgo.ApplicationCommand{
	{
		Name:        "stats",
		Description: "Displays your voice and text statistics on this server with a visual card.",
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
		Description: "Displays your consolidated global statistics across all servers with a visual card.",
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
		Description: "Compares statistics of two members in a direct 1v1 duel with a visual card.",
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
		},
	},
	{
		Name:        "server",
		Description: "Displays global statistics and live presence of this Discord server with a visual card.",
	},
	{
		Name:        "top",
		Description: "Visual Top 10 leaderboard card with custom filters.",
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
		Description: "Global Top 10 voice activity leaderboard across all tracked servers.",
	},
	{
		Name:        "help",
		Description: "Official command guide and features overview of Hourglass Bot.",
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

	// Immediate deferral to guarantee response within Discord's 3-second deadline
	_ = s.InteractionRespond(i.Interaction, &discordgo.InteractionResponse{
		Type: discordgo.InteractionResponseDeferredChannelMessageWithSource,
	})

	data := i.ApplicationCommandData()
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

func (h *BotHandler) handleStats(ctx context.Context, s *discordgo.Session, i *discordgo.InteractionCreate, isGlobal bool) {
	targetUser := i.Member.User
	data := i.ApplicationCommandData()
	for _, opt := range data.Options {
		if opt.Name == "user" || opt.Name == "utilisateur" {
			targetUser = opt.UserValue(s)
		}
	}

	userID, _ := strconv.ParseInt(targetUser.ID, 10, 64)
	serverID, _ := strconv.ParseInt(i.GuildID, 10, 64)

	var totalSeconds int64
	var totalMessages int64

	if isGlobal {
		_ = h.DB.Pool.QueryRow(ctx, `
			SELECT COALESCE(SUM(
				CASE WHEN left_at IS NOT NULL THEN duration_seconds 
				     ELSE EXTRACT(EPOCH FROM (NOW() - joined_at))::INT END
			), 0)
			FROM voice_sessions
			WHERE user_id = $1
		`, userID).Scan(&totalSeconds)

		_ = h.DB.Pool.QueryRow(ctx, `
			SELECT COALESCE(SUM(count), 0)
			FROM message_events
			WHERE user_id = $1
		`, userID).Scan(&totalMessages)
	} else {
		_ = h.DB.Pool.QueryRow(ctx, `
			SELECT COALESCE(SUM(
				CASE WHEN left_at IS NOT NULL THEN duration_seconds 
				     ELSE EXTRACT(EPOCH FROM (NOW() - joined_at))::INT END
			), 0)
			FROM voice_sessions
			WHERE user_id = $1 AND server_id = $2
		`, userID, serverID).Scan(&totalSeconds)

		_ = h.DB.Pool.QueryRow(ctx, `
			SELECT COALESCE(SUM(count), 0)
			FROM message_events
			WHERE user_id = $1 AND server_id = $2
		`, userID, serverID).Scan(&totalMessages)
	}

	serverName := "Discord Server"
	if guild, err := s.State.Guild(i.GuildID); err == nil && guild != nil {
		serverName = guild.Name
	}

	avatarURL := targetUser.AvatarURL("256")

	// Calculate Rank
	var rank int = 1
	if isGlobal {
		_ = h.DB.Pool.QueryRow(ctx, `
			SELECT COUNT(*) + 1
			FROM (
				SELECT user_id, SUM(CASE WHEN left_at IS NOT NULL THEN duration_seconds ELSE EXTRACT(EPOCH FROM (NOW() - joined_at))::INT END) AS s
				FROM voice_sessions
				GROUP BY user_id
				HAVING SUM(CASE WHEN left_at IS NOT NULL THEN duration_seconds ELSE EXTRACT(EPOCH FROM (NOW() - joined_at))::INT END) > $1
			) sub
		`, totalSeconds).Scan(&rank)
	} else {
		_ = h.DB.Pool.QueryRow(ctx, `
			SELECT COUNT(*) + 1
			FROM (
				SELECT user_id, SUM(CASE WHEN left_at IS NOT NULL THEN duration_seconds ELSE EXTRACT(EPOCH FROM (NOW() - joined_at))::INT END) AS s
				FROM voice_sessions
				WHERE server_id = $1
				GROUP BY user_id
				HAVING SUM(CASE WHEN left_at IS NOT NULL THEN duration_seconds ELSE EXTRACT(EPOCH FROM (NOW() - joined_at))::INT END) > $2
			) sub
		`, serverID, totalSeconds).Scan(&rank)
	}

	// Server join date
	joinDateStr := ""
	if !isGlobal {
		if member, err := s.GuildMember(i.GuildID, targetUser.ID); err == nil && member != nil && !member.JoinedAt.IsZero() {
			joinDateStr = member.JoinedAt.Format("01/02/2006")
		}
		if joinDateStr == "" {
			var firstJoin time.Time
			if err := h.DB.Pool.QueryRow(ctx, `SELECT MIN(joined_at) FROM voice_sessions WHERE user_id = $1 AND server_id = $2`, userID, serverID).Scan(&firstJoin); err == nil && !firstJoin.IsZero() {
				joinDateStr = firstJoin.Format("01/02/2006")
			}
		}
	}

	pngBytes, err := card.GenerateStatsCard(card.StatsCardParams{
		Username:      targetUser.Username,
		AvatarURL:     avatarURL,
		ServerName:    serverName,
		TotalSeconds:  totalSeconds,
		TotalMessages: totalMessages,
		Rank:          rank,
		JoinDate:      joinDateStr,
		IsGlobal:      isGlobal,
	})

	hours := float64(totalSeconds) / 3600.0
	scope := "on this server"
	if isGlobal {
		scope = "globally (all servers)"
	}

	fallbackContent := fmt.Sprintf(
		"**Statistics for %s** (%s):\n• Voice time: **%.1fh** (%d seconds)\n• Messages sent: **%d**\n[View full profile on dashboard](https://hourglassbot.net/profile/%d)",
		targetUser.Username, scope, hours, totalSeconds, totalMessages, userID,
	)

	linkContent := fmt.Sprintf("[View full profile on dashboard](https://hourglassbot.net/profile/%d)", userID)

	if err == nil && len(pngBytes) > 0 {
		_, _ = s.FollowupMessageCreate(i.Interaction, true, &discordgo.WebhookParams{
			Content: linkContent,
			Files: []*discordgo.File{
				{
					Name:        fmt.Sprintf("stats_%s.png", targetUser.Username),
					ContentType: "image/png",
					Reader:      bytes.NewReader(pngBytes),
				},
			},
		})
	} else {
		log.Printf("Error generating stats card: %v", err)
		_, _ = s.FollowupMessageCreate(i.Interaction, true, &discordgo.WebhookParams{
			Content: fallbackContent,
		})
	}
}

func (h *BotHandler) handleVersus(ctx context.Context, s *discordgo.Session, i *discordgo.InteractionCreate) {
	data := i.ApplicationCommandData()
	var u1, u2 *discordgo.User

	for _, opt := range data.Options {
		if opt.Name == "player1" || opt.Name == "joueur1" {
			u1 = opt.UserValue(s)
		} else if opt.Name == "player2" || opt.Name == "joueur2" {
			u2 = opt.UserValue(s)
		}
	}

	if u1 == nil || u2 == nil {
		_, _ = s.FollowupMessageCreate(i.Interaction, true, &discordgo.WebhookParams{
			Content: "Please designate two valid members for the duel.",
		})
		return
	}

	u1ID, _ := strconv.ParseInt(u1.ID, 10, 64)
	u2ID, _ := strconv.ParseInt(u2.ID, 10, 64)
	serverID, _ := strconv.ParseInt(i.GuildID, 10, 64)

	var u1Sec, u1Msg, u2Sec, u2Msg int64

	_ = h.DB.Pool.QueryRow(ctx, `
		SELECT COALESCE(SUM(
			CASE WHEN left_at IS NOT NULL THEN duration_seconds 
			     ELSE EXTRACT(EPOCH FROM (NOW() - joined_at))::INT END
		), 0)
		FROM voice_sessions
		WHERE user_id = $1 AND server_id = $2
	`, u1ID, serverID).Scan(&u1Sec)

	_ = h.DB.Pool.QueryRow(ctx, `
		SELECT COALESCE(SUM(count), 0)
		FROM message_events
		WHERE user_id = $1 AND server_id = $2
	`, u1ID, serverID).Scan(&u1Msg)

	_ = h.DB.Pool.QueryRow(ctx, `
		SELECT COALESCE(SUM(
			CASE WHEN left_at IS NOT NULL THEN duration_seconds 
			     ELSE EXTRACT(EPOCH FROM (NOW() - joined_at))::INT END
		), 0)
		FROM voice_sessions
		WHERE user_id = $1 AND server_id = $2
	`, u2ID, serverID).Scan(&u2Sec)

	_ = h.DB.Pool.QueryRow(ctx, `
		SELECT COALESCE(SUM(count), 0)
		FROM message_events
		WHERE user_id = $1 AND server_id = $2
	`, u2ID, serverID).Scan(&u2Msg)

	serverName := "Discord Server"
	if guild, err := s.State.Guild(i.GuildID); err == nil && guild != nil {
		serverName = guild.Name
	}

	u1Avatar := u1.AvatarURL("256")
	u2Avatar := u2.AvatarURL("256")

	pngBytes, err := card.GenerateVersusCard(card.VersusCardParams{
		U1Name:     u1.Username,
		U1Avatar:   u1Avatar,
		U1Seconds:  u1Sec,
		U1Msgs:     u1Msg,
		U2Name:     u2.Username,
		U2Avatar:   u2Avatar,
		U2Seconds:  u2Sec,
		U2Msgs:     u2Msg,
		ServerName: serverName,
	})

	versusLink := fmt.Sprintf("[View full comparison on dashboard](https://hourglassbot.net/versus?u1=%d&u2=%d)", u1ID, u2ID)

	if err == nil && len(pngBytes) > 0 {
		_, _ = s.FollowupMessageCreate(i.Interaction, true, &discordgo.WebhookParams{
			Content: fmt.Sprintf("**Duel: %s VS %s**\n%s", u1.Username, u2.Username, versusLink),
			Files: []*discordgo.File{
				{
					Name:        fmt.Sprintf("versus_%s_%s.png", u1.Username, u2.Username),
					ContentType: "image/png",
					Reader:      bytes.NewReader(pngBytes),
				},
			},
		})
	} else {
		log.Printf("Error generating versus card: %v", err)
		fallback := fmt.Sprintf(
			"**Duel: %s VS %s**\n\n• **%s**: %.1fh voice | %d msgs\n• **%s**: %.1fh voice | %d msgs\n\n%s",
			u1.Username, u2.Username,
			u1.Username, float64(u1Sec)/3600.0, u1Msg,
			u2.Username, float64(u2Sec)/3600.0, u2Msg,
			versusLink,
		)
		_, _ = s.FollowupMessageCreate(i.Interaction, true, &discordgo.WebhookParams{
			Content: fallback,
		})
	}
}

func (h *BotHandler) handleServerStats(ctx context.Context, s *discordgo.Session, i *discordgo.InteractionCreate) {
	serverID, _ := strconv.ParseInt(i.GuildID, 10, 64)

	var totalSeconds int64
	var totalMessages int64

	_ = h.DB.Pool.QueryRow(ctx, `
		SELECT COALESCE(SUM(
			CASE WHEN left_at IS NOT NULL THEN duration_seconds 
			     ELSE EXTRACT(EPOCH FROM (NOW() - joined_at))::INT END
		), 0)
		FROM voice_sessions
		WHERE server_id = $1
	`, serverID).Scan(&totalSeconds)

	_ = h.DB.Pool.QueryRow(ctx, `
		SELECT COALESCE(SUM(count), 0)
		FROM message_events
		WHERE server_id = $1
	`, serverID).Scan(&totalMessages)

	serverName := "Discord Server"
	iconURL := ""
	memberCount := 0
	voiceCount := 0
	onlineCount := 0

	guild, err := s.State.Guild(i.GuildID)
	if err != nil || guild == nil {
		guild, _ = s.Guild(i.GuildID)
	}

	if guild != nil {
		serverName = guild.Name
		iconURL = guild.IconURL("256")
		memberCount = guild.MemberCount
		voiceCount = len(guild.VoiceStates)
		for _, p := range guild.Presences {
			if p.Status != discordgo.StatusOffline {
				onlineCount++
			}
		}
	}

	pngBytes, err := card.GenerateServerCard(card.ServerCardParams{
		ServerID:      serverID,
		ServerName:    serverName,
		IconURL:       iconURL,
		TotalSeconds:  totalSeconds,
		TotalMessages: totalMessages,
		MemberCount:   memberCount,
		VoiceCount:    voiceCount,
		OnlineCount:   onlineCount,
	})

	hours := float64(totalSeconds) / 3600.0
	dashLink := fmt.Sprintf("[View server dashboard](https://hourglassbot.net/server/%d)", serverID)

	if err == nil && len(pngBytes) > 0 {
		_, _ = s.FollowupMessageCreate(i.Interaction, true, &discordgo.WebhookParams{
			Content: dashLink,
			Files: []*discordgo.File{
				{
					Name:        fmt.Sprintf("server_%d.png", serverID),
					ContentType: "image/png",
					Reader:      bytes.NewReader(pngBytes),
				},
			},
		})
	} else {
		log.Printf("Error generating server card: %v", err)
		fallback := fmt.Sprintf(
			"**Server Statistics for %s**:\n• Total voice time: **%.1fh** (%s)\n• Total messages: **%s**\n• Members: **%d**\n%s",
			serverName, hours, card.FormatDuration(totalSeconds), card.FormatNumber(totalMessages), memberCount, dashLink,
		)
		_, _ = s.FollowupMessageCreate(i.Interaction, true, &discordgo.WebhookParams{
			Content: fallback,
		})
	}
}

func (h *BotHandler) handleTopFiltered(ctx context.Context, s *discordgo.Session, i *discordgo.InteractionCreate, forceGlobal bool) {
	rankingType := "vocal"
	period := "all"
	scope := "server"
	if forceGlobal {
		scope = "global"
	}

	data := i.ApplicationCommandData()
	for _, opt := range data.Options {
		switch opt.Name {
		case "type":
			rankingType = opt.StringValue()
		case "period", "periode":
			period = opt.StringValue()
		case "scope", "portee":
			scope = opt.StringValue()
		}
	}

	serverID, _ := strconv.ParseInt(i.GuildID, 10, 64)
	isGlobal := forceGlobal || scope == "global"

	var query string
	var args []interface{}

	dateFilter := ""
	if period == "week" {
		dateFilter = "AND joined_at >= NOW() - INTERVAL '7 days'"
	} else if period == "month" {
		dateFilter = "AND joined_at >= NOW() - INTERVAL '30 days'"
	}

	if rankingType == "messages" {
		msgDateFilter := ""
		if period == "week" {
			msgDateFilter = "AND created_at >= NOW() - INTERVAL '7 days'"
		} else if period == "month" {
			msgDateFilter = "AND created_at >= NOW() - INTERVAL '30 days'"
		}

		if isGlobal {
			query = fmt.Sprintf(`
				SELECT m.user_id, COALESCE(u.username, 'Member'), COALESCE(u.avatar, ''), SUM(m.count) AS total_val
				FROM message_events m
				LEFT JOIN users u ON u.user_id = m.user_id
				WHERE 1=1 %s
				GROUP BY m.user_id, u.username, u.avatar
				ORDER BY total_val DESC
				LIMIT 10
			`, msgDateFilter)
		} else {
			query = fmt.Sprintf(`
				SELECT m.user_id, COALESCE(u.username, 'Member'), COALESCE(u.avatar, ''), SUM(m.count) AS total_val
				FROM message_events m
				LEFT JOIN users u ON u.user_id = m.user_id
				WHERE m.server_id = $1 %s
				GROUP BY m.user_id, u.username, u.avatar
				ORDER BY total_val DESC
				LIMIT 10
			`, msgDateFilter)
			args = append(args, serverID)
		}
	} else {
		if isGlobal {
			query = fmt.Sprintf(`
				SELECT vs.user_id, COALESCE(u.username, 'Member'), COALESCE(u.avatar, ''),
				       SUM(CASE WHEN vs.left_at IS NOT NULL THEN vs.duration_seconds 
				                ELSE EXTRACT(EPOCH FROM (NOW() - vs.joined_at))::INT END) AS total_val
				FROM voice_sessions vs
				LEFT JOIN users u ON u.user_id = vs.user_id
				WHERE 1=1 %s
				GROUP BY vs.user_id, u.username, u.avatar
				ORDER BY total_val DESC
				LIMIT 10
			`, dateFilter)
		} else {
			query = fmt.Sprintf(`
				SELECT vs.user_id, COALESCE(u.username, 'Member'), COALESCE(u.avatar, ''),
				       SUM(CASE WHEN vs.left_at IS NOT NULL THEN vs.duration_seconds 
				                ELSE EXTRACT(EPOCH FROM (NOW() - vs.joined_at))::INT END) AS total_val
				FROM voice_sessions vs
				LEFT JOIN users u ON u.user_id = vs.user_id
				WHERE vs.server_id = $1 %s
				GROUP BY vs.user_id, u.username, u.avatar
				ORDER BY total_val DESC
				LIMIT 10
			`, dateFilter)
			args = append(args, serverID)
		}
	}

	rows, err := h.DB.Pool.Query(ctx, query, args...)
	if err != nil {
		log.Printf("Error querying /top: %v", err)
		_, _ = s.FollowupMessageCreate(i.Interaction, true, &discordgo.WebhookParams{
			Content: "Error while fetching leaderboard data.",
		})
		return
	}
	defer rows.Close()

	periodLabel := "All-Time"
	if period == "month" {
		periodLabel = "Last 30 Days"
	} else if period == "week" {
		periodLabel = "Last 7 Days"
	}
	scopeLabel := "This Server"
	if isGlobal {
		scopeLabel = "Global"
	}

	var entries []card.TopEntry
	rank := 1
	for rows.Next() {
		var uID int64
		var username string
		var avatar string
		var totalVal int64
		if err := rows.Scan(&uID, &username, &avatar, &totalVal); err == nil {
			valStr := ""
			if rankingType == "messages" {
				valStr = card.FormatNumber(totalVal)
			} else {
				hours := float64(totalVal) / 3600.0
				valStr = fmt.Sprintf("%.1fh (%s)", hours, card.FormatDuration(totalVal))
			}

			entries = append(entries, card.TopEntry{
				Rank:     rank,
				Username: username,
				Avatar:   avatar,
				Value:    totalVal,
				ValueStr: valStr,
			})
			rank++
		}
	}

	webLink := fmt.Sprintf("[View full leaderboard on website](https://hourglassbot.net/server/%d)", serverID)
	if isGlobal {
		webLink = "[View full leaderboard on website](https://hourglassbot.net/top)"
	}

	if len(entries) == 0 {
		_, _ = s.FollowupMessageCreate(i.Interaction, true, &discordgo.WebhookParams{
			Content: fmt.Sprintf("No activity recorded for this period/category.\n%s", webLink),
		})
		return
	}

	// Generate Top 10 Leaderboard visual card
	pngBytes, err := card.GenerateTopCard(rankingType, periodLabel, scopeLabel, entries)
	if err == nil && len(pngBytes) > 0 {
		_, _ = s.FollowupMessageCreate(i.Interaction, true, &discordgo.WebhookParams{
			Content: webLink,
			Files: []*discordgo.File{
				{
					Name:        fmt.Sprintf("top_%s_%s.png", rankingType, period),
					ContentType: "image/png",
					Reader:      bytes.NewReader(pngBytes),
				},
			},
		})
	} else {
		log.Printf("Error generating top card: %v", err)
		fallback := fmt.Sprintf("**Top 10 Leaderboard — %s (%s • %s)**:\n\n", rankingType, periodLabel, scopeLabel)
		for _, e := range entries {
			fallback += fmt.Sprintf("#%d %s — %s\n", e.Rank, e.Username, e.ValueStr)
		}
		fallback += "\n" + webLink
		_, _ = s.FollowupMessageCreate(i.Interaction, true, &discordgo.WebhookParams{
			Content: fallback,
		})
	}
}

func (h *BotHandler) handleTop(ctx context.Context, s *discordgo.Session, i *discordgo.InteractionCreate, isGlobal bool) {
	h.handleTopFiltered(ctx, s, i, isGlobal)
}

func (h *BotHandler) handleHelp(ctx context.Context, s *discordgo.Session, i *discordgo.InteractionCreate) {
	pngBytes, err := card.GenerateHelpCard()

	webLink := "Explore the full web dashboard at: https://hourglassbot.net"

	if err == nil && len(pngBytes) > 0 {
		_, _ = s.FollowupMessageCreate(i.Interaction, true, &discordgo.WebhookParams{
			Content: webLink,
			Files: []*discordgo.File{
				{
					Name:        "hourglass_help.png",
					ContentType: "image/png",
					Reader:      bytes.NewReader(pngBytes),
				},
			},
		})
	} else {
		log.Printf("Error generating help card: %v", err)
		fallback := "**Hourglass Bot Command Guide**:\n" +
			"• `/stats [user]`: Voice & message stats on current server\n" +
			"• `/allstats [user]`: Consolidated global stats across all servers\n" +
			"• `/top [type] [period] [scope]`: Filtered Top 10 leaderboard\n" +
			"• `/alltop`: Global Top 10 voice leaderboard\n" +
			"• `/versus <p1> <p2>`: Direct 1v1 comparison duel\n" +
			"• `/server`: Server stats, voice activity & live presence\n" +
			"• `/help`: Displays this guide\n\n" +
			webLink
		_, _ = s.FollowupMessageCreate(i.Interaction, true, &discordgo.WebhookParams{
			Content: fallback,
		})
	}
}
