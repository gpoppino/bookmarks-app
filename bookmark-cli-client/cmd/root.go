package cmd

import (
	"fmt"
	"os"

	"github.com/gpoppino/bookmarks-cli/internal"
	"github.com/spf13/cobra"
)

var (
	apiURL string
	client *internal.Client
)

var rootCmd = &cobra.Command{
	Use:   "bookmarks",
	Short: "CLI client for the bookmarks API",
	PersistentPreRun: func(cmd *cobra.Command, args []string) {
		client = internal.NewClient(apiURL)
	},
}

func Execute() {
	if err := rootCmd.Execute(); err != nil {
		fmt.Fprintln(os.Stderr, err)
		os.Exit(1)
	}
}

func init() {
	defaultURL := "http://localhost:8000"
	if env := os.Getenv("BOOKMARKS_API_URL"); env != "" {
		defaultURL = env
	}
	rootCmd.PersistentFlags().StringVar(&apiURL, "api-url", defaultURL, "Backend API URL")
}
