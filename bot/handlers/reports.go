package handlers

import (
	"context"
	"fmt"
	"log"
	"strconv"
	"sync"
	"time"
	_ "time/tzdata" // the servers' time zones, whatever the system has

	"hourglass-bot/card"
	"hourglass-bot/database"

	"github.com/bwmarrin/discordgo"
)

// Automatic reports (website, server management > Reports): daily, weekly and monthly summaries of a server,
// posted in a channel at the chosen hour of the server's time zone. The image is a card drawn by the website,
// loaded by Discord from a signed address (embed), like the level-up cards.
//
//   - daily: at the chosen hour, the day before;
//   - weekly: on the chosen day at the chosen hour, the 7 days before;
//   - monthly: on the 1st at the chosen hour, the month before.
//
// Each report is booked in report_runs before being sent: never twice, even after a restart. A report missed while
// the bot was offline is still sent within 6 hours; after that it is skipped (an old report would only confuse).

const (
	reportTick        = time.Minute
	reportCatchUp     = 6 * time.Hour
	reportSendTimeout = 30 * time.Second
)

var reportsOnce sync.Once

func (h *BotHandler) startReports(s *discordgo.Session) {
	reportsOnce.Do(func() {
		go func() {
			ticker := time.NewTicker(reportTick)
			defer ticker.Stop()
			for {
				h.runDueReports(s)
				h.runReportRequests(s)
				<-ticker.C
			}
		}()
	})
}

// reportDue returns the last moment the report was due (at or before now, in now's location) and the first day of
// the period it covers.
func reportDue(kind string, now time.Time, hour, weekday int) (due, period time.Time) {
	loc := now.Location()
	day := func(t time.Time, offset int) time.Time {
		return time.Date(t.Year(), t.Month(), t.Day()+offset, 0, 0, 0, 0, loc)
	}
	at := func(t time.Time) time.Time { return time.Date(t.Year(), t.Month(), t.Day(), hour, 0, 0, 0, loc) }
	switch kind {
	case "weekly":
		goWeekday := time.Weekday((weekday + 1) % 7) // 0 = Monday on the website, time.Sunday = 0 in Go
		for i := 0; i <= 7; i++ {
			d := day(now, -i)
			if d.Weekday() == goWeekday && !at(d).After(now) {
				return at(d), day(d, -7)
			}
		}
	case "monthly":
		due = time.Date(now.Year(), now.Month(), 1, hour, 0, 0, 0, loc)
		if due.After(now) {
			due = time.Date(now.Year(), now.Month()-1, 1, hour, 0, 0, 0, loc)
		}
		return due, time.Date(due.Year(), due.Month()-1, 1, 0, 0, 0, 0, loc)
	}
	due = at(now)
	if due.After(now) {
		due = at(day(now, -1))
	}
	return due, day(due, -1)
}

func (h *BotHandler) runDueReports(s *discordgo.Session) {
	ctx, cancel := context.WithTimeout(context.Background(), 20*time.Second)
	defer cancel()
	reports, err := h.DB.LoadReportSettings(ctx)
	if err != nil {
		log.Printf("⚠️ [RAPPORTS] Réglages illisibles: %v", err)
		return
	}
	for _, r := range reports {
		loc, err := time.LoadLocation(r.Timezone)
		if err != nil {
			loc = time.UTC
		}
		now := time.Now().In(loc)
		due, period := reportDue(r.Kind, now, r.Hour, r.Weekday)
		if now.Sub(due) > reportCatchUp || due.Before(r.Since) {
			continue
		}
		booked, err := h.DB.ReserveReportRun(ctx, r.ServerID, r.Kind, period)
		if err != nil || !booked {
			continue
		}
		ok, detail := h.sendReport(s, r, period, false, 0)
		_ = h.DB.FinishReportRun(ctx, r.ServerID, r.Kind, period, ok, detail)
	}
}

// runReportRequests sends the tests asked from the website: the last finished period, marked as a test.
func (h *BotHandler) runReportRequests(s *discordgo.Session) {
	ctx, cancel := context.WithTimeout(context.Background(), 20*time.Second)
	defer cancel()
	requests, err := h.DB.PendingReportRequests(ctx)
	if err != nil {
		return
	}
	for _, req := range requests {
		r, err := h.DB.ReportSettingsFor(ctx, req.ServerID, req.Kind)
		if err != nil {
			_ = h.DB.FinishReportRequest(ctx, req.ID, false, err.Error())
			continue
		}
		loc, err := time.LoadLocation(r.Timezone)
		if err != nil {
			loc = time.UTC
		}
		_, period := reportDue(r.Kind, time.Now().In(loc), r.Hour, r.Weekday)
		ok, detail := h.sendReport(s, r, period, true, req.RequestedBy)
		_ = h.DB.FinishReportRequest(ctx, req.ID, ok, detail)
	}
}

// sendReport posts one report; returns (sent, journal detail).
func (h *BotHandler) sendReport(s *discordgo.Session, r database.ReportSettings, period time.Time, test bool, actor int64) (bool, string) {
	ctx, cancel := context.WithTimeout(context.Background(), reportSendTimeout)
	defer cancel()
	action := "report_sent"
	if test {
		action = "report_test"
	}
	periodText := period.Format("2006-01-02")
	entry := database.FeatureLog{ServerID: r.ServerID, Feature: "reports", Action: action, ActorID: actor, OK: true,
		Detail: r.Kind + " · " + periodText}
	fail := func(reason string) (bool, string) {
		entry.OK = false
		entry.Detail = r.Kind + " · " + periodText + " · " + reason
		_ = h.DB.LogFeature(ctx, entry)
		return false, reason
	}
	if r.ChannelID == 0 {
		return fail("no channel")
	}
	image := card.ReportImageURL(r.ServerID, r.Kind, periodText, r.Locale)
	if image == "" {
		return fail("CARD_TOKEN missing")
	}

	guildID := strconv.FormatInt(r.ServerID, 10)
	serverName := guildID
	if g, err := s.State.Guild(guildID); err == nil && g != nil {
		serverName = g.Name
	}
	langCode := guildLang(r.Locale)
	title := fmt.Sprintf(textIn("report_title_"+r.Kind, langCode), serverName)
	if test {
		title += " · " + textIn("report_test", langCode)
	}
	send := &discordgo.MessageSend{
		Embeds: []*discordgo.MessageEmbed{{
			Title: title, URL: "https://hourglassbot.net/server/" + guildID, Color: 0x717cf8,
			Image: &discordgo.MessageEmbedImage{URL: image},
		}},
		// Only the chosen role may be pinged (never @everyone or @here)
		AllowedMentions: &discordgo.MessageAllowedMentions{Parse: []discordgo.AllowedMentionType{}, Roles: []string{}},
	}
	if r.MentionRole != 0 && !test {
		role := strconv.FormatInt(r.MentionRole, 10)
		send.Content = "<@&" + role + ">"
		send.AllowedMentions.Roles = []string{role}
	}
	if _, err := s.ChannelMessageSendComplex(strconv.FormatInt(r.ChannelID, 10), send, discordgo.WithContext(ctx)); err != nil {
		log.Printf("⚠️ [RAPPORTS] Rapport %s de %s impossible: %v", r.Kind, guildID, err)
		return fail(discordError(err))
	}
	log.Printf("📊 [RAPPORTS] Rapport %s (%s) envoyé sur %s", r.Kind, periodText, guildID)
	_ = h.DB.LogFeature(ctx, entry)
	return true, ""
}

// textIn returns a text of the bot in a language (English when missing).
func textIn(key, lang string) string {
	if t, ok := messages[key][lang]; ok {
		return t
	}
	return messages[key]["en"]
}
