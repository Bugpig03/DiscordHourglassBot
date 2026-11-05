package handlers

import (
	"testing"

	"github.com/bwmarrin/discordgo"
)

// A member on two servers counts once, a bot (absent from members) does not count
func TestUniquePresence(t *testing.T) {
	members := map[string]struct{}{"a": {}, "b": {}, "c": {}, "d": {}}
	status := map[string]discordgo.Status{
		"a":   discordgo.StatusOnline,
		"b":   discordgo.StatusIdle,
		"c":   discordgo.StatusDoNotDisturb,
		"bot": discordgo.StatusOnline,
	}
	on, idle, dnd, off := uniquePresence(members, status)
	if on != 1 || idle != 1 || dnd != 1 || off != 1 {
		t.Fatalf("got %d %d %d %d, want 1 1 1 1", on, idle, dnd, off)
	}
}
