// Package card fetches the stat card images drawn by the website (one design for the site and the bot:
// member colors, banner and showcase badges come from the member's profile customization).
//
// Environment:
//   - CARD_TOKEN: secret shared with the website (its CARD_TOKEN); cards are disabled when empty.
//   - WEB_INTERNAL_URL: address of the website seen from the bot, e.g. http://hourglass-web:5002
//     on the same Docker network (default: https://hourglassbot.net).
package card

import (
	"context"
	"errors"
	"fmt"
	"io"
	"net/http"
	"net/url"
	"os"
	"strings"
	"time"
)

// ErrDisabled is returned while CARD_TOKEN is not configured: the commands answer with text.
var ErrDisabled = errors.New("CARD_TOKEN is not configured")

// ErrNotFound means the website has no data for this member or server.
var ErrNotFound = errors.New("no data for this card")

var client = &http.Client{Timeout: 12 * time.Second}

func baseURL() string {
	if v := strings.TrimSpace(os.Getenv("WEB_INTERNAL_URL")); v != "" {
		return strings.TrimRight(v, "/")
	}
	return "https://hourglassbot.net"
}

// Fetch returns the PNG of a card: kind is member, versus, top or server (see web/app/routes/cards.py).
func Fetch(ctx context.Context, kind string, params url.Values) ([]byte, error) {
	token := strings.TrimSpace(os.Getenv("CARD_TOKEN"))
	if token == "" {
		return nil, ErrDisabled
	}
	req, err := http.NewRequestWithContext(ctx, http.MethodGet, fmt.Sprintf("%s/internal/card/%s.png?%s", baseURL(), kind, params.Encode()), nil)
	if err != nil {
		return nil, err
	}
	req.Header.Set("X-Card-Token", token)
	resp, err := client.Do(req)
	if err != nil {
		return nil, err
	}
	defer resp.Body.Close()
	if resp.StatusCode == http.StatusNotFound && strings.HasPrefix(resp.Header.Get("Content-Type"), "application/json") {
		return nil, ErrNotFound
	}
	if resp.StatusCode != http.StatusOK || !strings.HasPrefix(resp.Header.Get("Content-Type"), "image/png") {
		return nil, fmt.Errorf("card %s: HTTP %d", kind, resp.StatusCode)
	}
	return io.ReadAll(io.LimitReader(resp.Body, 8<<20))
}

// FormatDuration converts seconds into human readable format (e.g., "45.2h", "142h" or "35m")
func FormatDuration(sec int64) string {
	if sec <= 0 {
		return "0m"
	}
	hours := float64(sec) / 3600.0
	if hours >= 1000 {
		return fmt.Sprintf("%dh", int64(hours))
	} else if hours >= 1.0 {
		return fmt.Sprintf("%.1fh", hours)
	}
	minutes := sec / 60
	if minutes > 0 {
		return fmt.Sprintf("%dm", minutes)
	}
	return fmt.Sprintf("%ds", sec)
}

// FormatNumber formats numbers with comma separators (e.g., 12,450)
func FormatNumber(n int64) string {
	in := fmt.Sprintf("%d", n)
	out := ""
	for i, c := range in {
		if (len(in)-i)%3 == 0 && i > 0 {
			out += ","
		}
		out += string(c)
	}
	return out
}
