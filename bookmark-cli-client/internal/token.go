package internal

import (
	"os"
	"path/filepath"
)

func SessionPath() (string, error) {
	configDir, err := os.UserConfigDir()
	if err != nil {
		return "", err
	}
	return filepath.Join(configDir, "bookmarks-cli", "session"), nil
}

func SaveToken(token string) error {
	path, err := SessionPath()
	if err != nil {
		return err
	}
	if err := os.MkdirAll(filepath.Dir(path), 0700); err != nil {
		return err
	}
	return os.WriteFile(path, []byte(token), 0600)
}

func LoadToken() (string, error) {
	path, err := SessionPath()
	if err != nil {
		return "", err
	}
	data, err := os.ReadFile(path)
	if err != nil {
		return "", err
	}
	return string(data), nil
}

func DeleteToken() error {
	path, err := SessionPath()
	if err != nil {
		return err
	}
	return os.Remove(path)
}
