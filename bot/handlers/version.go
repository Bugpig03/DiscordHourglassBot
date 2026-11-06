package handlers

import (
	"fmt"
	"runtime"
	"time"

	"github.com/bwmarrin/discordgo"
)

// Version, BuildDate and Commit are set at build time by the Dockerfile (-ldflags -X, from the git tag and the
// GitHub Actions run); Version keeps this value for a local build.
var (
	Version   = "3.7.5"
	BuildDate = "" // RFC 3339, e.g. 2026-11-05T17:42:38.000Z
	Commit    = ""
	StartedAt = time.Now()
)

const repoURL = "https://github.com/Bugpig03/DiscordHourglassBot"

// handleVersion answers /version (shown to server admins only, not listed in /help): which build is running
// and since when, to check that an update reached the server. Only the member who asked sees the answer.
func (h *BotHandler) handleVersion(s *discordgo.Session, i *discordgo.InteractionCreate) {
	build := msg(i, "version_local")
	if t, err := time.Parse(time.RFC3339, BuildDate); err == nil {
		build = fmt.Sprintf("<t:%d:f>", t.Unix())
	}
	commit := "—"
	if len(Commit) >= 7 {
		commit = fmt.Sprintf("[`%s`](%s/commit/%s)", Commit[:7], repoURL, Commit)
	}
	_ = s.InteractionRespond(i.Interaction, &discordgo.InteractionResponse{
		Type: discordgo.InteractionResponseChannelMessageWithSource,
		Data: &discordgo.InteractionResponseData{
			Flags: discordgo.MessageFlagsEphemeral,
			Embeds: []*discordgo.MessageEmbed{{
				Title: "Hourglass Bot v" + Version,
				URL:   fmt.Sprintf("%s/releases/tag/bot-v%s", repoURL, Version),
				Color: 0x717cf8,
				Fields: []*discordgo.MessageEmbedField{
					{Name: msg(i, "version_build"), Value: build, Inline: true},
					{Name: msg(i, "version_started"), Value: fmt.Sprintf("<t:%d:R>", StartedAt.Unix()), Inline: true},
					{Name: "Commit", Value: commit, Inline: true},
					{Name: msg(i, "version_servers"), Value: fmt.Sprintf("%d", len(s.State.Guilds)), Inline: true},
					{Name: "Go", Value: runtime.Version(), Inline: true},
				},
			}},
		},
	})
}
