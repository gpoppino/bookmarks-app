package internal

import (
	"os"
	"path/filepath"
	"testing"
)

func useTemporaryConfig(t *testing.T) string {
	t.Helper()
	root := t.TempDir()
	t.Setenv("HOME", root)
	t.Setenv("XDG_CONFIG_HOME", root)
	configDir, err := os.UserConfigDir()
	if err != nil {
		t.Fatalf("resolve config directory: %v", err)
	}
	return filepath.Join(configDir, "bookmarks-cli", "session")
}

func TestTokenSaveLoadAndDelete(t *testing.T) {
	expectedPath := useTemporaryConfig(t)
	path, err := SessionPath()
	if err != nil {
		t.Fatalf("SessionPath returned an error: %v", err)
	}
	if path != expectedPath {
		t.Fatalf("SessionPath = %q, want %q", path, expectedPath)
	}

	if _, err := LoadToken(); !os.IsNotExist(err) {
		t.Fatalf("LoadToken before save error = %v, want not-exist", err)
	}
	if err := SaveToken("first-token"); err != nil {
		t.Fatalf("SaveToken returned an error: %v", err)
	}
	info, err := os.Stat(path)
	if err != nil {
		t.Fatalf("stat session file: %v", err)
	}
	if info.Mode().Perm() != 0600 {
		t.Fatalf("session permissions = %o, want 600", info.Mode().Perm())
	}
	if token, err := LoadToken(); err != nil || token != "first-token" {
		t.Fatalf("LoadToken = %q, %v; want first-token", token, err)
	}

	if err := SaveToken("replacement-token"); err != nil {
		t.Fatalf("overwrite token: %v", err)
	}
	if token, err := LoadToken(); err != nil || token != "replacement-token" {
		t.Fatalf("LoadToken after overwrite = %q, %v", token, err)
	}
	if err := DeleteToken(); err != nil {
		t.Fatalf("DeleteToken returned an error: %v", err)
	}
	if _, err := os.Stat(path); !os.IsNotExist(err) {
		t.Fatalf("session file still exists after delete: %v", err)
	}
	if err := DeleteToken(); !os.IsNotExist(err) {
		t.Fatalf("second DeleteToken error = %v, want not-exist", err)
	}
}
