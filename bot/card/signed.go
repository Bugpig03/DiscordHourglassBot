package card

import (
	"crypto/hmac"
	"crypto/sha256"
	"encoding/hex"
	"fmt"
	"net/url"
	"os"
	"strings"
)

// Public, signed card addresses: Discord loads them itself as the image of an embed, so the bot needs no
// "Attach files" permission. Only the addresses signed with CARD_TOKEN work on the website (no guessing).
//
// Environment: WEB_PUBLIC_URL, the website's public address Discord can reach (default https://hourglassbot.net).

func publicURL() string {
	if v := strings.TrimSpace(os.Getenv("WEB_PUBLIC_URL")); v != "" {
		return strings.TrimRight(v, "/")
	}
	return "https://hourglassbot.net"
}

// sign is the website's levelup_signature: HMAC-SHA256 with CARD_TOKEN, first 32 hex characters.
func sign(token, message string) string {
	mac := hmac.New(sha256.New, []byte(token))
	mac.Write([]byte(message))
	return hex.EncodeToString(mac.Sum(nil))[:32]
}

// LevelupImageURL is the image of a level-up announcement; "" while CARD_TOKEN is not configured.
func LevelupImageURL(userID, serverID int64, level int, lang string) string {
	token := strings.TrimSpace(os.Getenv("CARD_TOKEN"))
	if token == "" {
		return ""
	}
	q := url.Values{"sig": {sign(token, fmt.Sprintf("levelup:%d:%d:%d", userID, serverID, level))}}
	if lang != "" {
		q.Set("lang", lang)
	}
	return fmt.Sprintf("%s/card/levelup/%d/%d/%d.png?%s", publicURL(), userID, serverID, level, q.Encode())
}
