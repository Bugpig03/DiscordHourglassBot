package handlers

import (
	"testing"
	"time"

	"hourglass-bot/card"
)

func TestReportDue(t *testing.T) {
	paris, _ := time.LoadLocation("Europe/Paris")
	d := func(y int, m time.Month, day, h, min int) time.Time { return time.Date(y, m, day, h, min, 0, 0, paris) }
	cases := []struct {
		kind          string
		now           time.Time
		hour, weekday int
		due, period   time.Time
	}{
		// daily at 20:00: at 20:05 the report of the day before is due; at 19:59, yesterday's 20:00 is the last one
		{"daily", d(2026, 11, 21, 20, 5), 20, 0, d(2026, 11, 21, 20, 0), d(2026, 11, 20, 0, 0)},
		{"daily", d(2026, 11, 21, 19, 59), 20, 0, d(2026, 11, 20, 20, 0), d(2026, 11, 19, 0, 0)},
		// weekly on Sunday (6) at 20:00; 2026-11-22 is a Sunday: the 7 days before (15 to 21)
		{"weekly", d(2026, 11, 22, 21, 0), 20, 6, d(2026, 11, 22, 20, 0), d(2026, 11, 15, 0, 0)},
		{"weekly", d(2026, 11, 25, 9, 0), 20, 6, d(2026, 11, 22, 20, 0), d(2026, 11, 15, 0, 0)},
		{"weekly", d(2026, 11, 22, 19, 0), 20, 6, d(2026, 11, 15, 20, 0), d(2026, 11, 8, 0, 0)},
		// monthly on the 1st at 9:00: the month before; also across the new year
		{"monthly", d(2026, 12, 1, 9, 30), 9, 0, d(2026, 12, 1, 9, 0), d(2026, 11, 1, 0, 0)},
		{"monthly", d(2026, 12, 1, 8, 0), 9, 0, d(2026, 11, 1, 9, 0), d(2026, 10, 1, 0, 0)},
		{"monthly", d(2027, 1, 1, 10, 0), 9, 0, d(2027, 1, 1, 9, 0), d(2026, 12, 1, 0, 0)},
	}
	for _, c := range cases {
		due, period := reportDue(c.kind, c.now, c.hour, c.weekday)
		if !due.Equal(c.due) || !period.Equal(c.period) {
			t.Errorf("%s at %s: due %s period %s, want %s / %s", c.kind, c.now, due, period, c.due, c.period)
		}
	}
}

func TestReportImageURL(t *testing.T) {
	t.Setenv("CARD_TOKEN", "secret")
	t.Setenv("WEB_PUBLIC_URL", "https://example.test")
	got := card.ReportImageURL(7, "weekly", "2026-11-15", "fr")
	// HMAC-SHA256("secret", "report:7:weekly:2026-11-15")[:32], as the website's report_signature
	want := "https://example.test/card/report/7/weekly/2026-11-15.png?lang=fr&sig=2925b5c782a3af76b7475ee26ad61710"
	if got != want {
		t.Errorf("ReportImageURL = %s", got)
	}
}

func TestReportTexts(t *testing.T) {
	for _, key := range []string{"report_title_daily", "report_title_weekly", "report_title_monthly", "report_test"} {
		if len(messages[key]) != 12 {
			t.Errorf("%s: %d languages", key, len(messages[key]))
		}
	}
}
