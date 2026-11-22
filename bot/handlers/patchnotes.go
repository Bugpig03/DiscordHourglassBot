package handlers

import (
	"context"
	"fmt"
	"log"
	"regexp"
	"strconv"
	"strings"
	"sync"
	"time"

	"hourglass-bot/database"

	"github.com/bwmarrin/discordgo"
)

// Patch notes on the official Discord server (website admin page > Patch notes): every new version of the website
// and of the bot is posted in the chosen channel with its CHANGELOG entry, one message per version, within a minute
// of the deploy. In an announcement channel the message is also published, so the servers following the channel
// get it too.

const (
	patchnoteTick       = time.Minute
	patchnoteMaxEmbed   = 4000 // Discord allows 4096 characters in an embed description
	patchnoteMaxMessage = 5800 // and 6000 characters in all the embeds of a message
	patchnoteTimeout    = 30 * time.Second
	patchnoteRepoURL    = "https://github.com/Bugpig03/DiscordHourglassBot/blob/main/"
	patchnoteWebColor   = 0x717cf8
	patchnoteBotColor   = 0x3fd1a0
	patchnoteMaxTitle   = 256
	patchnoteFooterTag  = "Hourglass"
)

var (
	patchnoteOnce   sync.Once
	changelogHeader = regexp.MustCompile(`^##\s+Version\s+([0-9][0-9A-Za-z.\-]*)\s+-\s+(.*?)\s+-\s+(\d{2}/\d{2}/\d{4})\s*$`)
)

// ParseChangelog reads the entries of a CHANGELOG ("## Version X - Title - dd/mm/yyyy" then the text), newest first.
func ParseChangelog(text string) []database.Patchnote {
	var out []database.Patchnote
	var current *database.Patchnote
	var lines []string
	flush := func() {
		if current != nil {
			current.Body = strings.TrimSpace(strings.Join(lines, "\n"))
			if current.Body != "" {
				out = append(out, *current)
			}
		}
		current, lines = nil, nil
	}
	for _, line := range strings.Split(strings.ReplaceAll(text, "\r\n", "\n"), "\n") {
		if m := changelogHeader.FindStringSubmatch(strings.TrimSpace(line)); m != nil {
			flush()
			current = &database.Patchnote{Version: m[1], Title: strings.TrimSpace(m[2]), Released: m[3]}
			continue
		}
		if strings.HasPrefix(line, "# ") || strings.HasPrefix(line, "## ") {
			flush()
			continue
		}
		if current != nil {
			lines = append(lines, strings.TrimRight(line, " \t"))
		}
	}
	flush()
	return out
}

// splitPatchnote cuts a text into parts of at most max characters, between lines (a single longer line is cut).
func splitPatchnote(body string, max int) []string {
	var parts []string
	var b strings.Builder
	push := func() {
		if s := strings.TrimSpace(b.String()); s != "" {
			parts = append(parts, s)
		}
		b.Reset()
	}
	for _, line := range strings.Split(body, "\n") {
		for len([]rune(line)) > max { // one line longer than a part
			r := []rune(line)
			push()
			parts = append(parts, string(r[:max]))
			line = string(r[max:])
		}
		if b.Len() > 0 && len([]rune(b.String()))+1+len([]rune(line)) > max {
			push()
		}
		if b.Len() > 0 {
			b.WriteString("\n")
		}
		b.WriteString(line)
	}
	push()
	return parts
}

// MergeEnglish adds the English entries (same versions) to the French ones.
func MergeEnglish(french, english []database.Patchnote) []database.Patchnote {
	byVersion := make(map[string]database.Patchnote, len(english))
	for _, e := range english {
		byVersion[e.Version] = e
	}
	out := make([]database.Patchnote, len(french))
	for i, f := range french {
		if e, ok := byVersion[f.Version]; ok {
			f.TitleEN, f.BodyEN = e.Title, e.Body
		}
		out[i] = f
	}
	return out
}

func patchnoteTitle(label, version, title string) string {
	t := fmt.Sprintf("%s v%s · %s", label, version, title)
	if r := []rune(t); len(r) > patchnoteMaxTitle {
		t = string(r[:patchnoteMaxTitle])
	}
	return t
}

func embedSize(e *discordgo.MessageEmbed) int {
	n := len([]rune(e.Title)) + len([]rune(e.Description))
	if e.Footer != nil {
		n += len([]rune(e.Footer.Text))
	}
	return n
}

// patchnoteEmbeds builds the embeds of a version: English first (when there is an English entry), then French; a
// long text takes several embeds.
func patchnoteEmbeds(p database.Patchnote) []*discordgo.MessageEmbed {
	color := patchnoteWebColor
	file := "web/CHANGELOG"
	frLabel, enLabel := "🌐 Site", "🌐 Website"
	if p.Component == "bot" {
		color, file, frLabel, enLabel = patchnoteBotColor, "bot/CHANGELOG", "🤖 Bot", "🤖 Bot"
	}
	var embeds []*discordgo.MessageEmbed
	add := func(title, url, body string) {
		for i, part := range splitPatchnote(body, patchnoteMaxEmbed) {
			e := &discordgo.MessageEmbed{Description: part, Color: color}
			if i == 0 {
				e.Title, e.URL = title, url
			}
			embeds = append(embeds, e)
		}
	}
	if strings.TrimSpace(p.BodyEN) != "" {
		title := p.TitleEN
		if title == "" {
			title = p.Title
		}
		add(patchnoteTitle(enLabel, p.Version, title), patchnoteRepoURL+file+".en.md", p.BodyEN)
		add("🇫🇷 "+patchnoteTitle(frLabel, p.Version, p.Title), patchnoteRepoURL+file+".md", p.Body)
	} else {
		add(patchnoteTitle(frLabel, p.Version, p.Title), patchnoteRepoURL+file+".md", p.Body)
	}
	if len(embeds) > 0 {
		embeds[len(embeds)-1].Footer = &discordgo.MessageEmbedFooter{Text: patchnoteFooterTag + " · " + p.Released}
	}
	return embeds
}

// packEmbeds groups the embeds into messages within Discord's limits (6000 characters and 10 embeds per message).
func packEmbeds(embeds []*discordgo.MessageEmbed) [][]*discordgo.MessageEmbed {
	var messages [][]*discordgo.MessageEmbed
	var current []*discordgo.MessageEmbed
	size := 0
	for _, e := range embeds {
		n := embedSize(e)
		if len(current) > 0 && (size+n > patchnoteMaxMessage || len(current) == 10) {
			messages = append(messages, current)
			current, size = nil, 0
		}
		current = append(current, e)
		size += n
	}
	if len(current) > 0 {
		messages = append(messages, current)
	}
	return messages
}

// startPatchnotes posts the waiting patch notes now and every minute (started once, whatever the reconnections).
func (h *BotHandler) startPatchnotes(s *discordgo.Session) {
	patchnoteOnce.Do(func() {
		go func() {
			ticker := time.NewTicker(patchnoteTick)
			defer ticker.Stop()
			for {
				h.runPatchnotes(s)
				<-ticker.C
			}
		}()
	})
}

func (h *BotHandler) runPatchnotes(s *discordgo.Session) {
	ctx, cancel := context.WithTimeout(context.Background(), patchnoteTimeout)
	defer cancel()
	settings, found, err := h.DB.LoadPatchnoteSettings(ctx)
	if err != nil || !found || settings.ChannelID == 0 {
		return
	}
	notes, err := h.DB.PendingPatchnotes(ctx)
	if err != nil {
		log.Printf("⚠️ [PATCH NOTES] Lecture impossible: %v", err)
		return
	}
	for _, p := range notes {
		booked, err := h.DB.ReservePatchnote(ctx, p.ID)
		if err != nil || !booked {
			continue
		}
		ok, detail := h.postPatchnote(s, settings, p)
		_ = h.DB.FinishPatchnote(ctx, p.ID, ok, detail)
	}
}

// postPatchnote sends one version (several messages when its text is long); returns (sent, detail for the admin).
func (h *BotHandler) postPatchnote(s *discordgo.Session, settings database.PatchnoteSettings, p database.Patchnote) (bool, string) {
	ctx, cancel := context.WithTimeout(context.Background(), patchnoteTimeout)
	defer cancel()
	channelID := strconv.FormatInt(settings.ChannelID, 10)
	announcement := false
	if ch, err := s.State.Channel(channelID); err == nil && ch != nil {
		announcement = ch.Type == discordgo.ChannelTypeGuildNews
	}
	messages := packEmbeds(patchnoteEmbeds(p))
	detail := ""
	for i, embeds := range messages {
		send := &discordgo.MessageSend{
			Embeds: embeds,
			// Only the chosen role may be pinged (never @everyone or @here)
			AllowedMentions: &discordgo.MessageAllowedMentions{Parse: []discordgo.AllowedMentionType{}, Roles: []string{}},
		}
		if i == 0 && settings.MentionRole != 0 {
			role := strconv.FormatInt(settings.MentionRole, 10)
			send.Content = "<@&" + role + ">"
			send.AllowedMentions.Roles = []string{role}
		}
		msg, err := s.ChannelMessageSendComplex(channelID, send, discordgo.WithContext(ctx))
		if err != nil {
			log.Printf("⚠️ [PATCH NOTES] %s v%s non postée: %v", p.Component, p.Version, err)
			return false, discordError(err)
		}
		// Announcement channel: published, so the servers following it receive it too
		if announcement {
			if _, err := s.ChannelMessageCrosspost(channelID, msg.ID, discordgo.WithContext(ctx)); err != nil {
				detail = "not published: " + discordError(err)
			}
		}
	}
	log.Printf("📣 [PATCH NOTES] %s v%s postée (%d message(s))", p.Component, p.Version, len(messages))
	return true, detail
}
