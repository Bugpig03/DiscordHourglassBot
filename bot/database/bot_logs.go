package database

import (
	"context"
	"fmt"
	"os"
	"regexp"
	"strings"
	"sync"
	"time"
)

// Bot log lines copied to the database, so the website admin page shows the latest ones without Portainer.
// The container output keeps every line; the table only keeps the BotLogKeep most recent ones.

const createBotLogsTable = `
	CREATE TABLE IF NOT EXISTS bot_logs (
		id BIGSERIAL PRIMARY KEY,
		created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT NOW(),
		line TEXT NOT NULL
	);
`

// BotLogKeep is the number of lines kept in bot_logs (the admin page shows the last 200).
const BotLogKeep = 500

const (
	botLogMaxLen    = 2000             // longer lines are cut
	botLogFlush     = 2 * time.Second  // lines are written in batches
	botLogBatch     = 100              // or as soon as this many are waiting
	botLogTrimEvery = 10 * time.Minute // older lines removed
)

// Date and time the log package puts in front of each line (the table has its own created_at)
var logPrefix = regexp.MustCompile(`^\d{4}/\d{2}/\d{2} \d{2}:\d{2}:\d{2}(\.\d+)? `)

// EnsureBotLogsTable creates the table when the migration was not applied (IF NOT EXISTS, harmless).
func (db *DB) EnsureBotLogsTable(ctx context.Context) error {
	_, err := db.Pool.Exec(ctx, createBotLogsTable)
	return err
}

type logLine struct {
	at   time.Time
	text string
}

// LogWriter is an io.Writer for log.SetOutput: each line is queued and written by a background goroutine.
// It never blocks the bot: when the queue is full (database down), lines are only in the container output.
type LogWriter struct {
	db     *DB
	lines  chan logLine
	stop   chan struct{}
	done   sync.WaitGroup
	failed bool // a write error is reported once on stderr, not on every batch
}

// NewLogWriter starts the background writer; Close flushes what is left.
func (db *DB) NewLogWriter() *LogWriter {
	w := &LogWriter{db: db, lines: make(chan logLine, 1000), stop: make(chan struct{})}
	w.done.Add(1)
	go w.run()
	return w
}

func (w *LogWriter) Write(p []byte) (int, error) {
	text := logPrefix.ReplaceAllString(strings.TrimRight(string(p), "\r\n"), "")
	if len(text) > botLogMaxLen {
		text = strings.ToValidUTF8(text[:botLogMaxLen], "") + "…"
	}
	if text != "" {
		select {
		case w.lines <- logLine{at: time.Now().UTC(), text: text}:
		default:
		}
	}
	return len(p), nil
}

// Close writes the lines still queued (the shutdown message included).
func (w *LogWriter) Close() {
	close(w.stop)
	w.done.Wait()
}

func (w *LogWriter) run() {
	defer w.done.Done()
	flush := time.NewTicker(botLogFlush)
	trim := time.NewTicker(botLogTrimEvery)
	defer flush.Stop()
	defer trim.Stop()
	var batch []logLine
	for {
		select {
		case l := <-w.lines:
			batch = append(batch, l)
			if len(batch) >= botLogBatch {
				batch = w.write(batch)
			}
		case <-flush.C:
			batch = w.write(batch)
		case <-trim.C:
			w.trim()
		case <-w.stop:
			for {
				select {
				case l := <-w.lines:
					batch = append(batch, l)
				default:
					w.write(batch)
					return
				}
			}
		}
	}
}

func (w *LogWriter) write(batch []logLine) []logLine {
	if len(batch) == 0 {
		return batch
	}
	times := make([]time.Time, len(batch))
	texts := make([]string, len(batch))
	for i, l := range batch {
		times[i], texts[i] = l.at, l.text
	}
	ctx, cancel := context.WithTimeout(context.Background(), 5*time.Second)
	defer cancel()
	_, err := w.db.Pool.Exec(ctx,
		`INSERT INTO bot_logs (created_at, line) SELECT * FROM unnest($1::timestamp[], $2::text[])`, times, texts)
	// Errors go to stderr directly: going through log would write to this writer again
	if err != nil && !w.failed {
		fmt.Fprintf(os.Stderr, "⚠️ Copie des logs en base impossible: %v\n", err)
	}
	w.failed = err != nil
	return batch[:0]
}

func (w *LogWriter) trim() {
	ctx, cancel := context.WithTimeout(context.Background(), 10*time.Second)
	defer cancel()
	_, err := w.db.Pool.Exec(ctx,
		`DELETE FROM bot_logs WHERE id <= (SELECT id FROM bot_logs ORDER BY id DESC OFFSET $1 LIMIT 1)`, BotLogKeep)
	if err != nil {
		fmt.Fprintf(os.Stderr, "⚠️ Nettoyage de bot_logs impossible: %v\n", err)
	}
}
