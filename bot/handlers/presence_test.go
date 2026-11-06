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

// Someone online but missing from the cached member lists still counts; a bot counts in the presence total,
// not among the people
func TestKnownAccounts(t *testing.T) {
	members := map[string]struct{}{"a": {}, "b": {}}
	bots := map[string]struct{}{"bot": {}}
	status := map[string]discordgo.Status{"a": discordgo.StatusOnline, "c": discordgo.StatusIdle, "bot": discordgo.StatusOnline}

	all := knownAccounts(members, bots, status, nil)
	on, idle, dnd, off := uniquePresence(all, status)
	if len(all) != 4 || on != 2 || idle != 1 || dnd != 0 || off != 1 {
		t.Fatalf("presence: %d accounts, %d %d %d %d, want 4 accounts, 2 1 0 1", len(all), on, idle, dnd, off)
	}
	if people := knownAccounts(members, nil, status, bots); len(people) != 3 {
		t.Fatalf("people: %d, want 3 (a, b, c)", len(people))
	}
}
