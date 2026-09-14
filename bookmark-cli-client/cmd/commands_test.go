package cmd

import (
	"encoding/json"
	"io"
	"net/http"
	"net/http/httptest"
	"testing"

	"github.com/gpoppino/bookmarks-cli/internal"
	"github.com/spf13/pflag"
)

func useCommandTestSession(t *testing.T) {
	t.Helper()
	root := t.TempDir()
	t.Setenv("HOME", root)
	t.Setenv("XDG_CONFIG_HOME", root)
	if err := internal.SaveToken("command-session"); err != nil {
		t.Fatalf("SaveToken: %v", err)
	}
}

func setFlag(t *testing.T, flag *pflag.Flag, value string) {
	t.Helper()
	previousValue := flag.Value.String()
	previousChanged := flag.Changed
	if err := flag.Value.Set(value); err != nil {
		t.Fatalf("set --%s: %v", flag.Name, err)
	}
	flag.Changed = true
	t.Cleanup(func() {
		_ = flag.Value.Set(previousValue)
		flag.Changed = previousChanged
	})
}

func TestMeCommandUsesAuthenticatedClient(t *testing.T) {
	useCommandTestSession(t)
	requestSeen := make(chan *http.Request, 1)
	server := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		requestSeen <- r.Clone(r.Context())
		w.Header().Set("Content-Type", "application/json")
		_, _ = io.WriteString(w, `{"id":3,"username":"alice","created_at":"2026-09-14T10:00:00Z"}`)
	}))
	defer server.Close()
	previousClient := client
	client = internal.NewClient(server.URL)
	t.Cleanup(func() { client = previousClient })

	if err := meCmd.RunE(meCmd, nil); err != nil {
		t.Fatalf("me command: %v", err)
	}
	request := <-requestSeen
	if request.Method != http.MethodGet || request.URL.Path != "/api/auth/me" {
		t.Fatalf("request = %s %s", request.Method, request.URL.Path)
	}
	if request.Header.Get("Cookie") != "access_token=command-session" {
		t.Fatalf("cookie = %q", request.Header.Get("Cookie"))
	}
}

func TestAddCommandParsesTagsAndCallsAPI(t *testing.T) {
	useCommandTestSession(t)
	bodySeen := make(chan map[string]any, 1)
	server := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		var body map[string]any
		_ = json.NewDecoder(r.Body).Decode(&body)
		bodySeen <- body
		w.Header().Set("Content-Type", "application/json")
		w.WriteHeader(http.StatusCreated)
		_, _ = io.WriteString(w, `{"id":9,"url":"https://example.test","tags":["go","cli"]}`)
	}))
	defer server.Close()
	previousClient := client
	client = internal.NewClient(server.URL)
	t.Cleanup(func() { client = previousClient })
	setFlag(t, addCmd.Flags().Lookup("url"), "https://example.test")
	setFlag(t, addCmd.Flags().Lookup("tags"), " go, ,cli ")

	if err := addCmd.RunE(addCmd, nil); err != nil {
		t.Fatalf("add command: %v", err)
	}
	body := <-bodySeen
	tags, ok := body["tags"].([]any)
	if !ok || len(tags) != 2 || tags[0] != "go" || tags[1] != "cli" {
		t.Fatalf("tags body = %#v", body["tags"])
	}
	if body["url"] != "https://example.test" {
		t.Fatalf("url body = %#v", body["url"])
	}
}

func TestAddCommandRejectsMissingURLWithoutCallingBackend(t *testing.T) {
	previousClient := client
	client = internal.NewClient("http://invalid.test")
	t.Cleanup(func() { client = previousClient })
	setFlag(t, addCmd.Flags().Lookup("url"), "")
	if err := addCmd.RunE(addCmd, nil); err == nil || err.Error() != "--url/-u is required" {
		t.Fatalf("add command error = %v", err)
	}
}
