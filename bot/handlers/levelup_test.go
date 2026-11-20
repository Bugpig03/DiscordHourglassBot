package handlers

import (
	"testing"

	"hourglass-bot/card"
)

func TestLevelForMatchesWebsite(t *testing.T) {
	// (seconds, messages, level) computed with calculate_user_xp_and_level on the website
	cases := []struct {
		seconds, messages int64
		level             int
	}{
		{0, 0, 1}, {59, 99, 1}, {60, 99, 2}, {0, 100, 2}, {0, 399, 2}, {0, 400, 3},
		{23940, 0, 2}, {24000, 0, 3}, {3600 * 100, 0, 8}, {3600 * 1000, 2500, 26}, {-5, -5, 1},
	}
	for _, c := range cases {
		if got := levelFor(c.seconds, c.messages); got != c.level {
			t.Errorf("levelFor(%d, %d) = %d, want %d", c.seconds, c.messages, got, c.level)
		}
	}
}

func TestShouldAnnounce(t *testing.T) {
	cases := []struct {
		prev, level, min, every int
		want                    bool
	}{
		{4, 5, 2, 1, true},    // each level
		{1, 2, 2, 1, true},    // the minimum itself
		{1, 2, 3, 1, false},   // under the minimum
		{4, 5, 2, 5, true},    // every 5: level 5
		{5, 6, 2, 5, false},   // every 5: level 6
		{8, 11, 2, 5, true},   // jumped over level 10
		{11, 14, 2, 5, false}, // nothing to announce in 12..14
		{3, 3, 1, 1, false},   // same level
	}
	for _, c := range cases {
		if got := shouldAnnounce(c.prev, c.level, c.min, c.every); got != c.want {
			t.Errorf("shouldAnnounce(%d, %d, min %d, every %d) = %v", c.prev, c.level, c.min, c.every, got)
		}
	}
}

func TestEscapeMarkdownAndLang(t *testing.T) {
	if got := escapeMarkdown("a*b_c`d"); got != `a\*b\_c\`+"`"+`d` {
		t.Errorf("escapeMarkdown: %q", got)
	}
	if guildLang("pt-BR") != "pt" || guildLang("en-US") != "en" || guildLang("zz") != "en" || guildLang("") != "en" {
		t.Error("guildLang")
	}
	for code, text := range messages["levelup_default"] {
		if !containsAll(text, "{membre}", "{niveau}") {
			t.Errorf("levelup_default[%s] misses a variable: %q", code, text)
		}
	}
}

func containsAll(s string, parts ...string) bool {
	for _, p := range parts {
		found := false
		for i := 0; i+len(p) <= len(s); i++ {
			if s[i:i+len(p)] == p {
				found = true
				break
			}
		}
		if !found {
			return false
		}
	}
	return true
}

func TestLevelupImageURL(t *testing.T) {
	t.Setenv("CARD_TOKEN", "secret")
	t.Setenv("WEB_PUBLIC_URL", "https://example.test/")
	got := card.LevelupImageURL(42, 7, 12, "fr")
	// Same signature as the website (levelup_signature): HMAC-SHA256("secret", "levelup:42:7:12")[:32]
	want := "https://example.test/card/levelup/42/7/12.png?lang=fr&sig=f314b5e18dc3a3255dbacfa081d64553"
	if got != want {
		t.Errorf("LevelupImageURL = %s", got)
	}
	t.Setenv("CARD_TOKEN", "")
	if card.LevelupImageURL(42, 7, 12, "fr") != "" {
		t.Error("no address without CARD_TOKEN")
	}
}
