"""Unit tests for password validation boundaries."""

import unittest

from password_policy import PasswordPolicyError, validate_password


class PasswordPolicyTests(unittest.TestCase):
    def test_accepts_passphrases_spaces_and_unicode(self):
        for password in (
            "a" * 15,
            "correct horse battery staple",
            "contraseña segura para mí",
            "é" * 36,
        ):
            with self.subTest(password=password):
                validate_password(password)

    def test_rejects_invalid_passwords_with_actionable_errors(self):
        cases = (
            ("short", "at least 15 characters"),
            (" " * 15, "only of whitespace"),
            ("valid-password\n", "control characters"),
            ("a" * 73, "72 UTF-8 bytes"),
            ("é" * 37, "72 UTF-8 bytes"),
        )
        for password, expected_error in cases:
            with self.subTest(expected_error=expected_error):
                with self.assertRaisesRegex(PasswordPolicyError, expected_error):
                    validate_password(password)


if __name__ == "__main__":
    unittest.main()
