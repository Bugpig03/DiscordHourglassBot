package handlers

import (
	"os"
	"strings"
	"testing"

	"hourglass-bot/database"
)

func TestParseChangelog(t *testing.T) {
	text := "# Title\n\n## Version 3.2.1 - Fix - 02/01/2026\n- **a**\n  - b\n\n## Version 3.2.0 - Big - 01/01/2026\n- c\n## Version 3.1.0 - Empty - 01/12/2025\n"
	got := ParseChangelog(text)
	if len(got) != 2 || got[0].Version != "3.2.1" || got[0].Title != "Fix" || got[0].Released != "02/01/2026" ||
		got[0].Body != "- **a**\n  - b" || got[1].Body != "- c" {
		t.Fatalf("parse: %+v", got)
	}
	// The real CHANGELOG built into the bot: the current version is its first entry
	raw, err := os.ReadFile("../CHANGELOG.md")
	if err != nil {
		t.Skip(err)
	}
	entries := ParseChangelog(string(raw))
	if len(entries) < 10 || entries[0].Version != Version {
		t.Fatalf("bot CHANGELOG: %d entries, first %q, Version %q", len(entries), entries[0].Version, Version)
	}
}

func TestSplitPatchnote(t *testing.T) {
	body := strings.Repeat("- line of text\n", 50) // 750 characters
	parts := splitPatchnote(body, 100)
	joined := strings.Join(parts, "\n")
	if strings.Count(joined, "line of text") != 50 {
		t.Fatal("lines lost")
	}
	for _, p := range parts {
		if len([]rune(p)) > 100 {
			t.Fatalf("part too long: %d", len(p))
		}
	}
	long := splitPatchnote(strings.Repeat("x", 250), 100)
	if len(long) != 3 || len(long[0]) != 100 {
		t.Fatalf("long line: %d parts", len(long))
	}
	if len(splitPatchnote("short", 4000)) != 1 {
		t.Fatal("short text cut")
	}
}

func TestPatchnoteEmbeds(t *testing.T) {
	both := patchnoteEmbeds(database.Patchnote{Component: "web", Version: "3.49.0", Title: "Titre", Body: "- fr",
		TitleEN: "Title", BodyEN: "- en", Released: "22/11/2026"})
	if len(both) != 2 || !strings.HasPrefix(both[0].Title, "🌐 Website v3.49.0 · Title") || both[0].Description != "- en" ||
		!strings.Contains(both[1].Title, "🇫🇷") || both[1].Description != "- fr" || both[0].Footer != nil || both[1].Footer == nil {
		t.Fatalf("EN then FR: %+v %+v", both[0], both[1])
	}
	if len(packEmbeds(both)) != 1 {
		t.Fatal("a short EN + FR version must be one message")
	}
	frOnly := patchnoteEmbeds(database.Patchnote{Component: "bot", Version: "3.12.0", Title: "Ancien", Body: "- fr"})
	if len(frOnly) != 1 || !strings.HasPrefix(frOnly[0].Title, "🤖 Bot v3.12.0 · Ancien") {
		t.Fatalf("French only: %+v", frOnly)
	}
	// Long texts: every message stays within Discord's limits, nothing is lost
	long := strings.Repeat("- a line of the changelog\n", 400) // ~10 400 characters per language
	embeds := patchnoteEmbeds(database.Patchnote{Component: "web", Version: "1", Title: "T", Body: long, TitleEN: "T", BodyEN: long})
	total := 0
	for _, m := range packEmbeds(embeds) {
		size := 0
		for _, e := range m {
			size += embedSize(e)
			if len([]rune(e.Description)) > 4096 {
				t.Fatal("embed over 4096")
			}
		}
		if size > 6000 || len(m) > 10 {
			t.Fatalf("message over the limits: %d chars, %d embeds", size, len(m))
		}
		total += len(m)
	}
	if total != len(embeds) {
		t.Fatal("embeds lost")
	}
}

func TestMergeEnglish(t *testing.T) {
	fr := []database.Patchnote{{Version: "2", Title: "Deux", Body: "b2"}, {Version: "1", Title: "Un", Body: "b1"}}
	en := []database.Patchnote{{Version: "2", Title: "Two", Body: "e2"}}
	got := MergeEnglish(fr, en)
	if got[0].TitleEN != "Two" || got[0].BodyEN != "e2" || got[1].BodyEN != "" {
		t.Fatalf("%+v", got)
	}
}
