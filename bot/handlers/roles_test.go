package handlers

import (
	"reflect"
	"testing"

	"hourglass-bot/database"
)

func cond(metric, scope string, min float64) database.RoleCondition {
	return database.RoleCondition{Metric: metric, Scope: scope, Min: min}
}

func TestConditionMet(t *testing.T) {
	m := database.MemberMetrics{VoiceTotal: 50 * 3600, Voice30d: 2 * 3600, MessagesAll: 1000, Messages30d: 10}
	cases := []struct {
		c    database.RoleCondition
		want bool
	}{
		{cond("voice", "total", 50), true},
		{cond("voice", "total", 51), false},
		{cond("voice", "30d", 2), true},
		{cond("voice", "30d", 3), false},
		{cond("messages", "total", 1000), true},
		{cond("messages", "30d", 11), false},
		// XP = 3000 + 1000 = 4000 -> level floor(sqrt(40)) + 1 = 7
		{cond("level", "total", 7), true},
		{cond("level", "total", 8), false},
		{cond("unknown", "total", 0), false},
	}
	for _, c := range cases {
		if got := conditionMet(c.c, m); got != c.want {
			t.Errorf("conditionMet(%+v) = %v, want %v", c.c, got, c.want)
		}
	}
}

func TestRuleMatch(t *testing.T) {
	m := database.MemberMetrics{VoiceTotal: 10 * 3600, MessagesAll: 5}
	both := []database.RoleCondition{cond("voice", "total", 5), cond("messages", "total", 100)}
	if ruleMet(database.RoleRule{Match: "all", Conditions: both}, m) {
		t.Error("all: one condition missing, must not match")
	}
	if !ruleMet(database.RoleRule{Match: "any", Conditions: both}, m) {
		t.Error("any: one condition met, must match")
	}
	if ruleMet(database.RoleRule{Match: "all"}, m) {
		t.Error("a rule without conditions never matches")
	}
}

func TestPlanMember(t *testing.T) {
	tiers := []database.RoleRule{
		{RoleID: 1, Match: "all", Conditions: []database.RoleCondition{cond("voice", "total", 1)}},
		{RoleID: 2, Match: "all", Conditions: []database.RoleCondition{cond("voice", "total", 10)}},
		{RoleID: 3, Match: "all", Conditions: []database.RoleCondition{cond("voice", "total", 100)}},
	}
	ladder := func(keep bool, t ...database.RoleRule) database.RoleLadder {
		return database.RoleLadder{KeepHighest: keep, Tiers: t}
	}
	m := database.MemberMetrics{VoiceTotal: 20 * 3600}
	set := func(ids ...int64) map[int64]bool {
		out := map[int64]bool{}
		for _, id := range ids {
			out[id] = true
		}
		return out
	}

	// Cumulative rule: both met roles given
	st := &database.RoleSettings{Ladders: []database.RoleLadder{ladder(false, tiers...)}, RemoveUnmet: true}
	if got := planMember(st, m, set(), set()); !reflect.DeepEqual(got.Add, []int64{1, 2}) || got.Remove != nil {
		t.Errorf("cumulative: %+v", got)
	}

	// Progression: only the highest met; the lower one the bot gave is removed, even without RemoveUnmet
	st = &database.RoleSettings{Ladders: []database.RoleLadder{ladder(true, tiers...)}}
	got := planMember(st, m, set(1), set(1))
	if !reflect.DeepEqual(got.Add, []int64{2}) || !reflect.DeepEqual(got.Remove, []int64{1}) {
		t.Errorf("progression: %+v", got)
	}

	// A role given by hand is never removed
	if got := planMember(st, m, set(1), set()); got.Remove != nil {
		t.Errorf("hand-given role removed: %+v", got)
	}

	// No longer met: removed with RemoveUnmet only
	low := database.MemberMetrics{}
	all := []database.RoleLadder{ladder(false, tiers...)}
	if got := planMember(&database.RoleSettings{Ladders: all, RemoveUnmet: true}, low, set(2), set(2)); !reflect.DeepEqual(got.Remove, []int64{2}) {
		t.Errorf("remove unmet: %+v", got)
	}
	if got := planMember(&database.RoleSettings{Ladders: all}, low, set(2), set(2)); got.Remove != nil {
		t.Errorf("kept when RemoveUnmet is off: %+v", got)
	}

	// Grant of a role removed by hand, no longer wanted: forgotten
	if got := planMember(&database.RoleSettings{Ladders: all}, low, set(), set(3)); !reflect.DeepEqual(got.Forget, []int64{3}) {
		t.Errorf("forget: %+v", got)
	}

	// Two rules, each with its own mode: a voice progression (highest only) and a stacked messages rule
	msgs := database.RoleRule{RoleID: 9, Match: "all", Conditions: []database.RoleCondition{cond("messages", "total", 1)}}
	two := &database.RoleSettings{Ladders: []database.RoleLadder{ladder(true, tiers...), ladder(false, msgs)}}
	mm := database.MemberMetrics{VoiceTotal: 20 * 3600, MessagesAll: 5}
	if got := planMember(two, mm, set(), set()); !reflect.DeepEqual(got.Add, []int64{2, 9}) {
		t.Errorf("two rules: %+v", got)
	}

	// A role replaced in one progression but wanted by another rule is kept
	other := database.RoleRule{RoleID: 1, Match: "all", Conditions: []database.RoleCondition{cond("messages", "total", 1)}}
	both := &database.RoleSettings{Ladders: []database.RoleLadder{ladder(true, tiers...), ladder(false, other)}}
	if got := planMember(both, mm, set(1, 2), set(1, 2)); got.Remove != nil {
		t.Errorf("role wanted elsewhere removed: %+v", got)
	}
}
