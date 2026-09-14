package internal

import (
	"encoding/json"
	"io"
	"net/http"
	"net/http/httptest"
	"net/url"
	"reflect"
	"strings"
	"testing"
)

type observedRequest struct {
	method      string
	path        string
	query       url.Values
	cookie      string
	contentType string
	body        map[string]any
}

func observeRequest(r *http.Request) observedRequest {
	body := map[string]any{}
	if r.Body != nil {
		_ = json.NewDecoder(r.Body).Decode(&body)
	}
	return observedRequest{
		method: r.Method, path: r.URL.Path, query: r.URL.Query(),
		cookie: r.Header.Get("Cookie"), contentType: r.Header.Get("Content-Type"),
		body: body,
	}
}

func TestLoginSendsCredentialsAndReturnsSessionCookie(t *testing.T) {
	requests := make(chan observedRequest, 1)
	server := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		requests <- observeRequest(r)
		http.SetCookie(w, &http.Cookie{Name: "access_token", Value: "session-value"})
		w.Header().Set("Content-Type", "application/json")
		_, _ = io.WriteString(w, `{}`)
	}))
	defer server.Close()

	token, err := NewClient(server.URL).Login("alice", "secret")
	if err != nil || token != "session-value" {
		t.Fatalf("Login = %q, %v; want session-value", token, err)
	}
	request := <-requests
	if request.method != http.MethodPost || request.path != "/api/auth/login" {
		t.Fatalf("request = %s %s", request.method, request.path)
	}
	if request.contentType != "application/json" {
		t.Fatalf("Content-Type = %q", request.contentType)
	}
	if !reflect.DeepEqual(request.body, map[string]any{
		"username": "alice", "password": "secret",
	}) {
		t.Fatalf("body = %#v", request.body)
	}
}

func TestAuthenticatedBookmarkClientRequests(t *testing.T) {
	useTemporaryConfig(t)
	if err := SaveToken("saved-session"); err != nil {
		t.Fatalf("SaveToken: %v", err)
	}
	requests := make(chan observedRequest, 5)
	server := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		requests <- observeRequest(r)
		w.Header().Set("Content-Type", "application/json")
		switch {
		case r.Method == http.MethodGet && r.URL.Path == "/api/bookmarks":
			_, _ = io.WriteString(w, `[{"id":7,"url":"https://example.test","tags":["go"]}]`)
		case r.Method == http.MethodPost && r.URL.Path == "/api/bookmarks":
			w.WriteHeader(http.StatusCreated)
			_, _ = io.WriteString(w, `{"id":7,"url":"https://example.test","tags":["go"]}`)
		case r.Method == http.MethodPut && r.URL.Path == "/api/bookmarks/7":
			_, _ = io.WriteString(w, `{"id":7,"url":"https://updated.test","tags":[]}`)
		case r.Method == http.MethodDelete && r.URL.Path == "/api/bookmarks/7":
			w.WriteHeader(http.StatusNoContent)
		case r.Method == http.MethodGet && r.URL.Path == "/api/tags":
			_, _ = io.WriteString(w, `[{"name":"go"}]`)
		default:
			http.NotFound(w, r)
		}
	}))
	defer server.Close()
	client := NewClient(server.URL)

	bookmarks, err := client.ListBookmarks("fast api", "go", 2, 10)
	if err != nil || len(bookmarks) != 1 || bookmarks[0].ID != 7 {
		t.Fatalf("ListBookmarks = %#v, %v", bookmarks, err)
	}
	created, err := client.AddBookmark("https://example.test", []string{"go"})
	if err != nil || created.ID != 7 {
		t.Fatalf("AddBookmark = %#v, %v", created, err)
	}
	updatedURL := "https://updated.test"
	updated, err := client.UpdateBookmark(7, &updatedURL, nil)
	if err != nil || updated.URL != updatedURL {
		t.Fatalf("UpdateBookmark = %#v, %v", updated, err)
	}
	if err := client.DeleteBookmark(7); err != nil {
		t.Fatalf("DeleteBookmark: %v", err)
	}
	tags, err := client.ListTags()
	if err != nil || len(tags) != 1 || tags[0].Name != "go" {
		t.Fatalf("ListTags = %#v, %v", tags, err)
	}

	observed := make([]observedRequest, 0, 5)
	for i := 0; i < 5; i++ {
		observed = append(observed, <-requests)
	}
	for _, request := range observed {
		if request.cookie != "access_token=saved-session" {
			t.Errorf("%s %s cookie = %q", request.method, request.path, request.cookie)
		}
	}
	if got := observed[0].query.Encode(); got != "limit=10&search=fast+api&skip=2&tag=go" {
		t.Errorf("list query = %q", got)
	}
	if !reflect.DeepEqual(observed[1].body, map[string]any{
		"url": "https://example.test", "tags": []any{"go"},
	}) {
		t.Errorf("add body = %#v", observed[1].body)
	}
	if !reflect.DeepEqual(observed[2].body, map[string]any{"url": updatedURL}) {
		t.Errorf("update body = %#v", observed[2].body)
	}
}

func TestClientSurfacesAPIErrorsAndMissingSessions(t *testing.T) {
	useTemporaryConfig(t)
	client := NewClient("http://invalid.test")
	if _, err := client.Me(); err == nil || !strings.Contains(err.Error(), "not logged in") {
		t.Fatalf("Me error = %v, want not logged in", err)
	}

	server := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		w.Header().Set("Content-Type", "application/json")
		w.WriteHeader(http.StatusConflict)
		_, _ = io.WriteString(w, `{"detail":"username already taken"}`)
	}))
	defer server.Close()
	_, err := NewClient(server.URL).Register("alice", "secret")
	if err == nil || err.Error() != "API error 409: username already taken" {
		t.Fatalf("Register error = %v", err)
	}
}
