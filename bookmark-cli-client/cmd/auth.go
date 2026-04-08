package cmd

import (
	"bufio"
	"fmt"
	"os"
	"strings"
	"syscall"

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
	fmt.Printf("%s: ", label)
	pw, err := term.ReadPassword(syscall.Stdin)
	fmt.Println()
	if err != nil {
		return "", err
	}
	return string(pw), nil
}

func resolveCredentials(username, password string) (string, string, error) {
	var err error
	if username == "" {
		username, err = promptString("Username")
		if err != nil {
			return "", "", err
		}
	}
	if password == "" {
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
		password, _ := cmd.Flags().GetString("password")
		var err error
		username, password, err = resolveCredentials(username, password)
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
		password, _ := cmd.Flags().GetString("password")
		var err error
		username, password, err = resolveCredentials(username, password)
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
		currentPassword, _ := cmd.Flags().GetString("current-password")
		newPassword, _ := cmd.Flags().GetString("new-password")
		var err error
		if currentPassword == "" {
			currentPassword, err = promptPassword("Current password")
			if err != nil {
				return err
			}
		}
		if newPassword == "" {
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
	loginCmd.Flags().StringP("password", "p", "", "Password")

	registerCmd.Flags().StringP("username", "n", "", "Username")
	registerCmd.Flags().StringP("password", "p", "", "Password")

	changePasswordCmd.Flags().StringP("current-password", "c", "", "Current password")
	changePasswordCmd.Flags().StringP("new-password", "n", "", "New password")

	rootCmd.AddCommand(loginCmd, registerCmd, logoutCmd, meCmd, changePasswordCmd)
}
