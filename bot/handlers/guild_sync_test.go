package handlers

import (
	"testing"

	"github.com/bwmarrin/discordgo"
)

func TestGuildPermissions(t *testing.T) {
	guild := &discordgo.Guild{
		ID:      "1",
		OwnerID: "99",
		Roles: []*discordgo.Role{
			{ID: "1", Permissions: discordgo.PermissionViewChannel},   // @everyone
			{ID: "2", Permissions: discordgo.PermissionSendMessages},  // member role
			{ID: "3", Permissions: discordgo.PermissionAdministrator}, // admin role
			{ID: "4", Permissions: discordgo.PermissionManageRoles},   // not held
		},
	}
	got := guildPermissions(guild, "10", []string{"2"})
	want := int64(discordgo.PermissionViewChannel | discordgo.PermissionSendMessages)
	if got != want {
		t.Fatalf("everyone + role: got %d, want %d", got, want)
	}
	if got&discordgo.PermissionManageRoles != 0 {
		t.Fatal("a role the member does not hold must not count")
	}
	if guildPermissions(guild, "10", []string{"3"}) != discordgo.PermissionAll {
		t.Fatal("an administrator has every permission")
	}
	if guildPermissions(guild, "99", nil) != discordgo.PermissionAll {
		t.Fatal("the owner has every permission")
	}
}

func TestDangerousPermissions(t *testing.T) {
	for _, p := range []int64{discordgo.PermissionAdministrator, discordgo.PermissionManageGuild, discordgo.PermissionBanMembers} {
		if dangerousPermissions&p == 0 {
			t.Fatalf("permission %d should be dangerous", p)
		}
	}
	if dangerousPermissions&(discordgo.PermissionSendMessages|discordgo.PermissionViewChannel) != 0 {
		t.Fatal("ordinary permissions must stay allowed")
	}
}
