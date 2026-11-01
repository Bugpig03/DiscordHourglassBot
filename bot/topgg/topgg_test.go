package topgg

import (
	"context"
	"encoding/json"
	"net/http"
	"net/http/httptest"
	"testing"
)

func TestPostStats(t *testing.T) {
	var got struct {
		path, auth string
		body       map[string]int
	}
	srv := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		got.path, got.auth = r.URL.Path, r.Header.Get("Authorization")
		_ = json.NewDecoder(r.Body).Decode(&got.body)
		if got.auth != "good-token" && got.auth != "Bearer Bearer-only" {
			w.WriteHeader(http.StatusUnauthorized)
			_, _ = w.Write([]byte(`{"error":"Unauthorized"}`))
			return
		}
		w.WriteHeader(http.StatusOK)
	}))
	defer srv.Close()
	apiBase = srv.URL

	if err := PostStats(context.Background(), "1210665993328926750", "good-token", 47); err != nil {
		t.Fatalf("unexpected error: %v", err)
	}
	if got.path != "/bots/1210665993328926750/stats" || got.body["server_count"] != 47 {
		t.Fatalf("wrong request: %+v", got)
	}
	if err := PostStats(context.Background(), "1210665993328926750", "bad-token", 47); err == nil {
		t.Fatal("a 401 must be reported as an error")
	}
	// A token only accepted with "Bearer " (newer project tokens): the retry adds it
	got.auth = ""
	if err := PostStats(context.Background(), "1210665993328926750", "Bearer-only", 12); err != nil || got.auth != "Bearer Bearer-only" {
		t.Fatalf("expected a Bearer retry, got %q, %v", got.auth, err)
	}
}
