package database

import (
	"context"
	"log"
	"os"
	"strings"
	"testing"
)

func TestLogPrefixStripped(t *testing.T) {
	cases := map[string]string{
		"2026/11/01 10:00:00 ✅ Pool PostgreSQL connecté":            "✅ Pool PostgreSQL connecté",
		"2026/11/01 10:00:00.123456 ⚠️ test":                        "⚠️ test",
		"sans date":                                                 "sans date",
		"2026/11/01 10:00:00 ligne avec 2026/11/01 10:00:00 dedans": "ligne avec 2026/11/01 10:00:00 dedans",
	}
	for in, want := range cases {
		if got := logPrefix.ReplaceAllString(in, ""); got != want {
			t.Errorf("%q: got %q, want %q", in, got, want)
		}
	}
}

// Writes through the log package into bot_logs; runs only with HOURGLASS_TEST_DATABASE_URL (a dev database).
func TestLogWriterDatabase(t *testing.T) {
	url := os.Getenv("HOURGLASS_TEST_DATABASE_URL")
	if url == "" {
		t.Skip("HOURGLASS_TEST_DATABASE_URL not set")
	}
	db, err := New(url)
	if err != nil {
		t.Fatal(err)
	}
	defer db.Close()
	ctx := context.Background()
	if err := db.EnsureBotLogsTable(ctx); err != nil {
		t.Fatal(err)
	}
	w := db.NewLogWriter()
	logger := log.New(w, "", log.LstdFlags)
	logger.Printf("test-logwriter ❌ erreur %d", 1)
	logger.Printf("test-logwriter long %s", strings.Repeat("é", botLogMaxLen))
	w.Close()

	rows, err := db.Pool.Query(ctx, `SELECT line FROM bot_logs WHERE line LIKE 'test-logwriter%' ORDER BY id`)
	if err != nil {
		t.Fatal(err)
	}
	var lines []string
	for rows.Next() {
		var l string
		_ = rows.Scan(&l)
		lines = append(lines, l)
	}
	rows.Close()
	_, _ = db.Pool.Exec(ctx, `DELETE FROM bot_logs WHERE line LIKE 'test-logwriter%'`)
	if len(lines) != 2 || lines[0] != "test-logwriter ❌ erreur 1" || len(lines[1]) > botLogMaxLen+4 {
		t.Fatalf("unexpected lines: %d %q", len(lines), lines[0])
	}
}
