package internal

import (
	"bytes"
	"encoding/json"
	"fmt"
	"io"
	"net/http"
	"net/url"
	"strconv"
	"time"
)

type Client struct {
	BaseURL    string
	HTTPClient *http.Client
}

func NewClient(baseURL string) *Client {
	return &Client{
		BaseURL:    baseURL,
		HTTPClient: &http.Client{Timeout: 30 * time.Second},
	}
}

type User struct {
	ID        int       `json:"id"`
	Username  string    `json:"username"`
	CreatedAt time.Time `json:"created_at"`
}

type Bookmark struct {
	ID          int       `json:"id"`
	URL         string    `json:"url"`
	Title       string    `json:"title"`
	Description string    `json:"description"`
	Tags        []string  `json:"tags"`
	CreatedAt   time.Time `json:"created_at"`
}

type Tag struct {
	Name string `json:"name"`
}

type apiError struct {
	Detail string `json:"detail"`
}

func (c *Client) do(method, path string, body any) (*http.Response, error) {
	var bodyReader io.Reader
	if body != nil {
		data, err := json.Marshal(body)
		if err != nil {
			return nil, err
		}
		bodyReader = bytes.NewReader(data)
	}
	req, err := http.NewRequest(method, c.BaseURL+path, bodyReader)
	if err != nil {
		return nil, err
	}
	if body != nil {
		req.Header.Set("Content-Type", "application/json")
	}
	return c.HTTPClient.Do(req)
}

func (c *Client) doAuthed(method, path string, body any) (*http.Response, error) {
	token, err := LoadToken()
	if err != nil {
		return nil, fmt.Errorf("not logged in: run 'bookmarks login' first")
	}
	var bodyReader io.Reader
	if body != nil {
		data, err := json.Marshal(body)
		if err != nil {
			return nil, err
		}
		bodyReader = bytes.NewReader(data)
	}
	req, err := http.NewRequest(method, c.BaseURL+path, bodyReader)
	if err != nil {
		return nil, err
	}
	if body != nil {
		req.Header.Set("Content-Type", "application/json")
	}
	req.Header.Set("Cookie", "access_token="+token)
	return c.HTTPClient.Do(req)
}

func readAPIError(resp *http.Response) error {
	body, _ := io.ReadAll(resp.Body)
	var apiErr apiError
	if json.Unmarshal(body, &apiErr) == nil && apiErr.Detail != "" {
		return fmt.Errorf("API error %d: %s", resp.StatusCode, apiErr.Detail)
	}
	return fmt.Errorf("API error %d", resp.StatusCode)
}

func (c *Client) Login(username, password string) (string, error) {
	payload := map[string]string{"username": username, "password": password}
	resp, err := c.do("POST", "/api/auth/login", payload)
	if err != nil {
		return "", err
	}
	defer resp.Body.Close()
	if resp.StatusCode != http.StatusOK {
		return "", readAPIError(resp)
	}
	for _, cookie := range resp.Cookies() {
		if cookie.Name == "access_token" {
			return cookie.Value, nil
		}
	}
	return "", fmt.Errorf("no access_token cookie in response")
}

func (c *Client) Register(username, password string) (User, error) {
	payload := map[string]string{"username": username, "password": password}
	resp, err := c.do("POST", "/api/auth/register", payload)
	if err != nil {
		return User{}, err
	}
	defer resp.Body.Close()
	if resp.StatusCode != http.StatusOK && resp.StatusCode != http.StatusCreated {
		return User{}, readAPIError(resp)
	}
	var user User
	if err := json.NewDecoder(resp.Body).Decode(&user); err != nil {
		return User{}, err
	}
	return user, nil
}

func (c *Client) Logout() error {
	resp, err := c.doAuthed("POST", "/api/auth/logout", nil)
	if err != nil {
		return err
	}
	defer resp.Body.Close()
	if resp.StatusCode != http.StatusOK {
		return readAPIError(resp)
	}
	return nil
}

func (c *Client) Me() (User, error) {
	resp, err := c.doAuthed("GET", "/api/auth/me", nil)
	if err != nil {
		return User{}, err
	}
	defer resp.Body.Close()
	if resp.StatusCode != http.StatusOK {
		return User{}, readAPIError(resp)
	}
	var user User
	if err := json.NewDecoder(resp.Body).Decode(&user); err != nil {
		return User{}, err
	}
	return user, nil
}

func (c *Client) ChangePassword(currentPassword, newPassword string) error {
	payload := map[string]string{
		"current_password": currentPassword,
		"new_password":     newPassword,
	}
	resp, err := c.doAuthed("PUT", "/api/auth/password", payload)
	if err != nil {
		return err
	}
	defer resp.Body.Close()
	if resp.StatusCode != http.StatusOK {
		return readAPIError(resp)
	}
	return nil
}

func (c *Client) ListBookmarks(search, tag string, skip, limit int) ([]Bookmark, error) {
	params := url.Values{}
	if search != "" {
		params.Set("search", search)
	}
	if tag != "" {
		params.Set("tag", tag)
	}
	if skip > 0 {
		params.Set("skip", strconv.Itoa(skip))
	}
	if limit > 0 {
		params.Set("limit", strconv.Itoa(limit))
	}
	path := "/api/bookmarks"
	if len(params) > 0 {
		path += "?" + params.Encode()
	}
	resp, err := c.doAuthed("GET", path, nil)
	if err != nil {
		return nil, err
	}
	defer resp.Body.Close()
	if resp.StatusCode != http.StatusOK {
		return nil, readAPIError(resp)
	}
	var bookmarks []Bookmark
	if err := json.NewDecoder(resp.Body).Decode(&bookmarks); err != nil {
		return nil, err
	}
	return bookmarks, nil
}

func (c *Client) AddBookmark(bookmarkURL string, tags []string) (Bookmark, error) {
	payload := map[string]any{"url": bookmarkURL, "tags": tags}
	resp, err := c.doAuthed("POST", "/api/bookmarks", payload)
	if err != nil {
		return Bookmark{}, err
	}
	defer resp.Body.Close()
	if resp.StatusCode != http.StatusOK && resp.StatusCode != http.StatusCreated {
		return Bookmark{}, readAPIError(resp)
	}
	var bookmark Bookmark
	if err := json.NewDecoder(resp.Body).Decode(&bookmark); err != nil {
		return Bookmark{}, err
	}
	return bookmark, nil
}

func (c *Client) UpdateBookmark(id int, bookmarkURL *string, tags *[]string) (Bookmark, error) {
	payload := map[string]any{}
	if bookmarkURL != nil {
		payload["url"] = *bookmarkURL
	}
	if tags != nil {
		payload["tags"] = *tags
	}
	resp, err := c.doAuthed("PUT", "/api/bookmarks/"+strconv.Itoa(id), payload)
	if err != nil {
		return Bookmark{}, err
	}
	defer resp.Body.Close()
	if resp.StatusCode != http.StatusOK {
		return Bookmark{}, readAPIError(resp)
	}
	var bookmark Bookmark
	if err := json.NewDecoder(resp.Body).Decode(&bookmark); err != nil {
		return Bookmark{}, err
	}
	return bookmark, nil
}

func (c *Client) DeleteBookmark(id int) error {
	resp, err := c.doAuthed("DELETE", "/api/bookmarks/"+strconv.Itoa(id), nil)
	if err != nil {
		return err
	}
	defer resp.Body.Close()
	if resp.StatusCode != http.StatusOK && resp.StatusCode != http.StatusNoContent {
		return readAPIError(resp)
	}
	return nil
}

func (c *Client) ListTags() ([]Tag, error) {
	resp, err := c.doAuthed("GET", "/api/tags", nil)
	if err != nil {
		return nil, err
	}
	defer resp.Body.Close()
	if resp.StatusCode != http.StatusOK {
		return nil, readAPIError(resp)
	}
	var tags []Tag
	if err := json.NewDecoder(resp.Body).Decode(&tags); err != nil {
		return nil, err
	}
	return tags, nil
}
