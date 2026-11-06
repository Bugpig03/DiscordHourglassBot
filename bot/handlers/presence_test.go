package handlers

import (
	"testing"

	"github.com/bwmarrin/discordgo"
)

// Each account counts once with its status; an account missing from the list (left the servers) does not count
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
