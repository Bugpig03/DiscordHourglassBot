// Package topgg sends the bot's server count to top.gg, which shows it on the bot's page (top.gg cannot see it
// by itself: a bot that never posts its stats shows 0 servers).
//
// Environment:
//   - TOPGG_TOKEN: API token of the bot on top.gg (project dashboard → Integrations & API; not a webhook).
//     Nothing is sent when empty.
package topgg

import (
	"bytes"
	"context"
	"encoding/json"
	"errors"
	"fmt"
	"io"
	"log"
	"net/http"
	"os"
	"strings"
	"sync"
	"time"

	"github.com/bwmarrin/discordgo"
)

// Interval between two posts: top.gg updates the figure a few times an hour at most.
const Interval = 30 * time.Minute

var (
	client = &http.Client{Timeout: 15 * time.Second}
	once   sync.Once
	// apiBase is the top.gg API root (a test server in the tests)
	apiBase = "https://top.gg/api"
)

// Start posts the server count shortly after startup, then every Interval. Called on each READY (reconnections
// included): only the first call starts the loop.
func Start(s *discordgo.Session) {
	token := strings.TrimSpace(os.Getenv("TOPGG_TOKEN"))
	if token == "" {
		return
	}
	once.Do(func() {
		go func() {
			time.Sleep(1 * time.Minute) // let the GUILD_CREATE events fill the state first
			for {
				post(s, token)
				time.Sleep(Interval)
			}
		}()
	})
}

func post(s *discordgo.Session, token string) {
	if s.State == nil || s.State.User == nil {
		return
	}
	count := len(s.State.Guilds)
	if count == 0 {
		return // never overwrite the figure with 0 during a reconnection
	}
	ctx, cancel := context.WithTimeout(context.Background(), 15*time.Second)
	defer cancel()
	if err := PostStats(ctx, s.State.User.ID, token, count); err != nil {
		log.Printf("⚠️ top.gg : envoi du nombre de serveurs impossible : %v", err)
		return
	}
	log.Printf("📊 top.gg : %d serveur(s) envoyé(s)", count)
}

// PostStats sends server_count for the bot to the top.gg API (v0 stats endpoint). Legacy tokens go as they are;
// tokens of the newer Integrations & API page may need "Bearer ": on a 401 the call is retried once with it.
func PostStats(ctx context.Context, botID, token string, serverCount int) error {
	err := postStats(ctx, botID, token, serverCount)
	if errors.Is(err, errUnauthorized) && !strings.HasPrefix(token, "Bearer ") {
		err = postStats(ctx, botID, "Bearer "+token, serverCount)
	}
	return err
}

var errUnauthorized = errors.New("token refused")

func postStats(ctx context.Context, botID, authorization string, serverCount int) error {
	body, _ := json.Marshal(map[string]int{"server_count": serverCount})
	req, err := http.NewRequestWithContext(ctx, http.MethodPost, fmt.Sprintf("%s/bots/%s/stats", apiBase, botID), bytes.NewReader(body))
	if err != nil {
		return err
	}
	req.Header.Set("Authorization", authorization)
	req.Header.Set("Content-Type", "application/json")
	resp, err := client.Do(req)
	if err != nil {
		return err
	}
	defer resp.Body.Close()
	if resp.StatusCode == http.StatusUnauthorized || resp.StatusCode == http.StatusForbidden {
		msg, _ := io.ReadAll(io.LimitReader(resp.Body, 300))
		return fmt.Errorf("%w (HTTP %d : %s)", errUnauthorized, resp.StatusCode, strings.TrimSpace(string(msg)))
	}
	if resp.StatusCode >= 300 {
		msg, _ := io.ReadAll(io.LimitReader(resp.Body, 300))
		return fmt.Errorf("HTTP %d : %s", resp.StatusCode, strings.TrimSpace(string(msg)))
	}
	return nil
}
