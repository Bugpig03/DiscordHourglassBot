package handlers

import (
	"testing"

	"github.com/bwmarrin/discordgo"
)

// Someone online but missing from the cached member lists still counts; a bot is left out of the people
func TestKnownAccounts(t *testing.T) {
	members := map[string]struct{}{"a": {}, "b": {}}
	bots := map[string]struct{}{"bot": {}}
	status := map[string]discordgo.Status{"a": discordgo.StatusOnline, "c": discordgo.StatusIdle, "bot": discordgo.StatusOnline}

	if all := knownAccounts(members, bots, status, nil); len(all) != 4 {
		t.Fatalf("all accounts: %d, want 4 (a, b, c, bot)", len(all))
	}
	if people := knownAccounts(members, nil, status, bots); len(people) != 3 {
		t.Fatalf("people: %d, want 3 (a, b, c)", len(people))
	}
}
