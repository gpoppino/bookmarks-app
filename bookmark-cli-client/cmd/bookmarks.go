package cmd

import (
	"fmt"
	"os"
	"strings"
	"text/tabwriter"

	"github.com/spf13/cobra"
)

var listCmd = &cobra.Command{
	Use:   "list",
	Short: "List bookmarks",
	RunE: func(cmd *cobra.Command, args []string) error {
		tag, _ := cmd.Flags().GetString("tag")
		search, _ := cmd.Flags().GetString("search")
		skip, _ := cmd.Flags().GetInt("skip")
		limit, _ := cmd.Flags().GetInt("limit")

		bookmarks, err := client.ListBookmarks(search, tag, skip, limit)
		if err != nil {
			return err
		}

		w := tabwriter.NewWriter(os.Stdout, 0, 0, 2, ' ', 0)
		fmt.Fprintln(w, "ID\tURL\tTITLE\tTAGS\tCREATED")
		for _, b := range bookmarks {
			tags := strings.Join(b.Tags, ",")
			created := b.CreatedAt.Format("2006-01-02")
			title := b.Title
			if len(title) > 40 {
				title = title[:37] + "..."
			}
			fmt.Fprintf(w, "%d\t%s\t%s\t%s\t%s\n", b.ID, b.URL, title, tags, created)
		}
		w.Flush()
		return nil
	},
}

var addCmd = &cobra.Command{
	Use:   "add",
	Short: "Add a bookmark",
	RunE: func(cmd *cobra.Command, args []string) error {
		bookmarkURL, _ := cmd.Flags().GetString("url")
		if bookmarkURL == "" {
			return fmt.Errorf("--url/-u is required")
		}
		tagsStr, _ := cmd.Flags().GetString("tags")
		var tags []string
		if tagsStr != "" {
			for _, t := range strings.Split(tagsStr, ",") {
				t = strings.TrimSpace(t)
				if t != "" {
					tags = append(tags, t)
				}
			}
		}

		bookmark, err := client.AddBookmark(bookmarkURL, tags)
		if err != nil {
			return err
		}
		fmt.Printf("Added bookmark (id=%d): %s\n", bookmark.ID, bookmark.URL)
		return nil
	},
}

var deleteCmd = &cobra.Command{
	Use:   "delete",
	Short: "Delete a bookmark",
	RunE: func(cmd *cobra.Command, args []string) error {
		id, _ := cmd.Flags().GetInt("id")
		if id == 0 {
			return fmt.Errorf("--id/-i is required")
		}

		fmt.Printf("Delete bookmark %d? [y/N]: ", id)
		var confirm string
		fmt.Scanln(&confirm)
		if strings.ToLower(strings.TrimSpace(confirm)) != "y" {
			fmt.Println("Cancelled.")
			return nil
		}

		if err := client.DeleteBookmark(id); err != nil {
			return err
		}
		fmt.Printf("Deleted bookmark %d\n", id)
		return nil
	},
}

var tagsCmd = &cobra.Command{
	Use:   "tags",
	Short: "List all tags",
	RunE: func(cmd *cobra.Command, args []string) error {
		tags, err := client.ListTags()
		if err != nil {
			return err
		}
		for _, t := range tags {
			fmt.Println(t.Name)
		}
		return nil
	},
}

func init() {
	listCmd.Flags().StringP("tag", "t", "", "Filter by tag")
	listCmd.Flags().StringP("search", "s", "", "Search term")
	listCmd.Flags().Int("skip", 0, "Number of results to skip")
	listCmd.Flags().Int("limit", 0, "Maximum number of results")

	addCmd.Flags().StringP("url", "u", "", "URL to bookmark (required)")
	addCmd.Flags().StringP("tags", "t", "", "Comma-separated tags")

	deleteCmd.Flags().IntP("id", "i", 0, "Bookmark ID to delete (required)")

	rootCmd.AddCommand(listCmd, addCmd, deleteCmd, tagsCmd)
}
