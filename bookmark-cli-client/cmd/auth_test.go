package cmd

import (
	"strings"
	"testing"

	"github.com/spf13/cobra"
)

func TestPasswordValueFlagsAreNotRegistered(t *testing.T) {
	tests := []struct {
		name               string
		command            *cobra.Command
		forbiddenFlags     []string
		forbiddenShorthand []string
	}{
		{"login", loginCmd, []string{"password"}, []string{"p"}},
		{"register", registerCmd, []string{"password"}, []string{"p"}},
		{
			"change-password",
			changePasswordCmd,
			[]string{"current-password", "new-password"},
			[]string{"c", "n"},
		},
	}

	for _, test := range tests {
		t.Run(test.name, func(t *testing.T) {
			for _, name := range test.forbiddenFlags {
				if test.command.Flags().Lookup(name) != nil {
					t.Fatalf("password-bearing flag %q is still registered", name)
				}
			}
			for _, shorthand := range test.forbiddenShorthand {
				if test.command.Flags().ShorthandLookup(shorthand) != nil {
					t.Fatalf("password-bearing shorthand %q is still registered", shorthand)
				}
			}
			stdinFlag := test.command.Flags().Lookup("password-stdin")
			if stdinFlag == nil {
				t.Fatal("--password-stdin is not registered")
			}
			if stdinFlag.DefValue != "false" {
				t.Fatal("--password-stdin must be opt-in")
			}
		})
	}
}

func TestReadPasswords(t *testing.T) {
	passwords, err := readPasswords(strings.NewReader(" current password \r\nnew password\n"), 2)
	if err != nil {
		t.Fatalf("readPasswords returned an error: %v", err)
	}
	if passwords[0] != " current password " {
		t.Fatalf("current password was modified: %q", passwords[0])
	}
	if passwords[1] != "new password" {
		t.Fatalf("unexpected new password: %q", passwords[1])
	}
}

func TestReadPasswordsRejectsMissingAndEmptyLines(t *testing.T) {
	for name, input := range map[string]string{
		"missing": "only-one\n",
		"empty":   "current\n\n",
	} {
		t.Run(name, func(t *testing.T) {
			if _, err := readPasswords(strings.NewReader(input), 2); err == nil {
				t.Fatal("expected an error")
			}
		})
	}
}

func TestPasswordStdinRequiresUsername(t *testing.T) {
	_, _, err := resolveCredentials("", true, strings.NewReader("password\n"))
	if err == nil || !strings.Contains(err.Error(), "--username is required") {
		t.Fatalf("expected username requirement, got %v", err)
	}
}

func TestPasswordStdinResolvesCredentials(t *testing.T) {
	username, password, err := resolveCredentials(
		"alice", true, strings.NewReader("secret password\n"),
	)
	if err != nil {
		t.Fatalf("resolveCredentials returned an error: %v", err)
	}
	if username != "alice" || password != "secret password" {
		t.Fatalf("unexpected credentials: username=%q password=%q", username, password)
	}
}
