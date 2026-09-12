package cmd

import (
	"bufio"
	"fmt"
	"io"
	"os"
	"strings"

	"github.com/gpoppino/bookmarks-cli/internal"
	"github.com/spf13/cobra"
	"golang.org/x/term"
)

func promptString(label string) (string, error) {
	fmt.Printf("%s: ", label)
	reader := bufio.NewReader(os.Stdin)
	val, err := reader.ReadString('\n')
	if err != nil {
		return "", err
	}
	return strings.TrimSpace(val), nil
}

func promptPassword(label string) (string, error) {
	stdin := int(os.Stdin.Fd())
	if !term.IsTerminal(stdin) {
		return "", fmt.Errorf("interactive password prompt requires a terminal; use --password-stdin for explicit non-interactive input")
	}
	fmt.Printf("%s: ", label)
	pw, err := term.ReadPassword(stdin)
	fmt.Println()
	if err != nil {
		return "", err
	}
	return string(pw), nil
}

func readPasswords(reader io.Reader, count int) ([]string, error) {
	scanner := bufio.NewScanner(reader)
	passwords := make([]string, 0, count)
	for len(passwords) < count {
		if !scanner.Scan() {
			if err := scanner.Err(); err != nil {
				return nil, fmt.Errorf("failed to read password from stdin: %w", err)
			}
			return nil, fmt.Errorf("expected %d password line(s) on stdin, received %d", count, len(passwords))
		}
		password := scanner.Text()
		if password == "" {
			return nil, fmt.Errorf("password line %d on stdin is empty", len(passwords)+1)
		}
		passwords = append(passwords, password)
	}
	return passwords, nil
}

func resolveCredentials(username string, passwordStdin bool, stdin io.Reader) (string, string, error) {
	var err error
	if passwordStdin && username == "" {
		return "", "", fmt.Errorf("--username is required with --password-stdin")
	}
	if username == "" {
		username, err = promptString("Username")
		if err != nil {
			return "", "", err
		}
	}
	var password string
	if passwordStdin {
		passwords, err := readPasswords(stdin, 1)
		if err != nil {
			return "", "", err
		}
		password = passwords[0]
	} else {
		password, err = promptPassword("Password")
		if err != nil {
			return "", "", err
		}
	}
	return username, password, nil
}

var loginCmd = &cobra.Command{
	Use:   "login",
	Short: "Log in and save session token",
	RunE: func(cmd *cobra.Command, args []string) error {
		username, _ := cmd.Flags().GetString("username")
		passwordStdin, _ := cmd.Flags().GetBool("password-stdin")
		var err error
		username, password, err := resolveCredentials(username, passwordStdin, os.Stdin)
		if err != nil {
			return err
		}
		token, err := client.Login(username, password)
		if err != nil {
			return err
		}
		if err := internal.SaveToken(token); err != nil {
			return fmt.Errorf("failed to save session: %w", err)
		}
		fmt.Printf("Logged in as %s\n", username)
		return nil
	},
}

var registerCmd = &cobra.Command{
	Use:   "register",
	Short: "Register a new user",
	RunE: func(cmd *cobra.Command, args []string) error {
		username, _ := cmd.Flags().GetString("username")
		passwordStdin, _ := cmd.Flags().GetBool("password-stdin")
		var err error
		username, password, err := resolveCredentials(username, passwordStdin, os.Stdin)
		if err != nil {
			return err
		}
		user, err := client.Register(username, password)
		if err != nil {
			return err
		}
		fmt.Printf("Registered user: %s (id=%d)\n", user.Username, user.ID)
		return nil
	},
}

var logoutCmd = &cobra.Command{
	Use:   "logout",
	Short: "Log out and remove local session",
	RunE: func(cmd *cobra.Command, args []string) error {
		if err := client.Logout(); err != nil {
			fmt.Fprintf(os.Stderr, "Warning: server logout failed: %v\n", err)
		}
		if err := internal.DeleteToken(); err != nil && !os.IsNotExist(err) {
			return fmt.Errorf("failed to remove session file: %w", err)
		}
		fmt.Println("Logged out.")
		return nil
	},
}

var meCmd = &cobra.Command{
	Use:   "me",
	Short: "Show current user info",
	RunE: func(cmd *cobra.Command, args []string) error {
		user, err := client.Me()
		if err != nil {
			return err
		}
		fmt.Printf("Username:  %s\n", user.Username)
		fmt.Printf("ID:        %d\n", user.ID)
		fmt.Printf("Created:   %s\n", user.CreatedAt.Format("2006-01-02 15:04:05"))
		return nil
	},
}

var changePasswordCmd = &cobra.Command{
	Use:   "change-password",
	Short: "Change your password",
	RunE: func(cmd *cobra.Command, args []string) error {
		passwordStdin, _ := cmd.Flags().GetBool("password-stdin")
		var currentPassword, newPassword string
		if passwordStdin {
			passwords, err := readPasswords(os.Stdin, 2)
			if err != nil {
				return err
			}
			currentPassword, newPassword = passwords[0], passwords[1]
		} else {
			var err error
			currentPassword, err = promptPassword("Current password")
			if err != nil {
				return err
			}
			newPassword, err = promptPassword("New password")
			if err != nil {
				return err
			}
			confirm, err := promptPassword("Confirm new password")
			if err != nil {
				return err
			}
			if newPassword != confirm {
				return fmt.Errorf("passwords do not match")
			}
		}
		if err := client.ChangePassword(currentPassword, newPassword); err != nil {
			return err
		}
		fmt.Println("Password updated successfully.")
		return nil
	},
}

func init() {
	loginCmd.Flags().StringP("username", "n", "", "Username")
	loginCmd.Flags().Bool("password-stdin", false, "Read password from stdin (non-interactive)")

	registerCmd.Flags().StringP("username", "n", "", "Username")
	registerCmd.Flags().Bool("password-stdin", false, "Read password from stdin (non-interactive)")

	changePasswordCmd.Flags().Bool("password-stdin", false, "Read current and new passwords from two stdin lines (non-interactive)")

	rootCmd.AddCommand(loginCmd, registerCmd, logoutCmd, meCmd, changePasswordCmd)
}
