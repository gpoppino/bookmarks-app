"""Regression tests for startup-time authentication configuration validation."""
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


BACKEND_DIRECTORY = Path(__file__).resolve().parent


class SecretKeyConfigurationTests(unittest.TestCase):
    def import_backend(
        self,
        expression="main.SECRET_KEY",
        systemd_credentials=None,
        **environment,
    ):
        process_environment = os.environ.copy()
        process_environment.pop("APP_ENV", None)
        process_environment.pop("SECRET_KEY", None)
        process_environment.pop("AUTO_TAGGING_ENABLED", None)
        process_environment.pop("OPENAI_API_KEY", None)
        process_environment.pop("CREDENTIALS_DIRECTORY", None)
        process_environment.update(environment)
        process_environment["PYTHONPATH"] = str(BACKEND_DIRECTORY)

        with tempfile.TemporaryDirectory() as directory:
            if systemd_credentials is not None:
                credentials_directory = Path(directory) / "credentials"
                credentials_directory.mkdir()
                for name, value in systemd_credentials.items():
                    (credentials_directory / name).write_text(
                        value,
                        encoding="utf-8",
                    )
                process_environment["CREDENTIALS_DIRECTORY"] = str(
                    credentials_directory
                )

            return subprocess.run(
                [sys.executable, "-c", f"import main; print({expression})"],
                cwd=directory,
                env=process_environment,
                capture_output=True,
                text=True,
                check=False,
            )

    def assert_configuration_error(self, result, message):
        self.assertNotEqual(result.returncode, 0)
        self.assertIn(message, result.stderr)

    def test_missing_secret_key_fails_closed_by_default(self):
        result = self.import_backend()
        self.assert_configuration_error(result, "SECRET_KEY is required outside development")

    def test_missing_secret_key_fails_in_non_development_environment(self):
        result = self.import_backend(APP_ENV="staging")
        self.assert_configuration_error(result, "SECRET_KEY is required outside development")

    def test_short_and_development_keys_fail_outside_development(self):
        short = self.import_backend(APP_ENV="production", SECRET_KEY="too-short")
        self.assert_configuration_error(short, "at least 32 characters")

        development = self.import_backend(
            APP_ENV="production",
            SECRET_KEY="dev-secret-key-change-in-production",
        )
        self.assert_configuration_error(development, "cannot be used outside development")

    def test_strong_secret_key_allows_production_startup(self):
        secret_key = "a-strong-random-production-key-with-32-chars"
        result = self.import_backend(APP_ENV="production", SECRET_KEY=secret_key)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout.strip(), secret_key)

    def test_systemd_credential_allows_production_startup(self):
        secret_key = "a-systemd-credential-with-more-than-32-characters\n"
        result = self.import_backend(
            APP_ENV="production",
            systemd_credentials={"secret_key": secret_key},
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout.strip(), secret_key.strip())

    def test_systemd_credential_takes_precedence_over_environment(self):
        credential = "the-systemd-credential-is-the-selected-secret-key"
        result = self.import_backend(
            APP_ENV="production",
            SECRET_KEY="the-environment-variable-is-not-the-selected-key",
            systemd_credentials={"secret_key": credential},
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout.strip(), credential)

    def test_openai_systemd_credential_enables_automatic_tagging(self):
        result = self.import_backend(
            expression="main.tag_suggester.enabled",
            APP_ENV="production",
            AUTO_TAGGING_ENABLED="true",
            systemd_credentials={
                "secret_key": "a-systemd-secret-key-with-more-than-32-characters",
                "openai_api_key": "systemd-openai-api-key\n",
            },
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout.strip(), "True")

    def test_openai_systemd_credential_takes_precedence_over_environment(self):
        credential = "systemd-openai-api-key"
        result = self.import_backend(
            expression='main.load_tagging_environment()["OPENAI_API_KEY"]',
            APP_ENV="production",
            OPENAI_API_KEY="environment-openai-api-key",
            systemd_credentials={
                "secret_key": "a-systemd-secret-key-with-more-than-32-characters",
                "openai_api_key": credential,
            },
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout.strip(), credential)

    def test_explicit_development_allows_the_local_key(self):
        result = self.import_backend(APP_ENV="development")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout.strip(), "dev-secret-key-change-in-production")

    def test_session_cookie_secure_flag_is_environment_aware(self):
        development = self.import_backend(
            expression="main.SESSION_COOKIE_SECURE",
            APP_ENV="development",
        )
        self.assertEqual(development.returncode, 0, development.stderr)
        self.assertEqual(development.stdout.strip(), "False")

        for environment in ("production", "staging"):
            with self.subTest(environment=environment):
                deployed = self.import_backend(
                    expression="main.SESSION_COOKIE_SECURE",
                    APP_ENV=environment,
                    SECRET_KEY="a-strong-random-production-key-with-32-chars",
                )
                self.assertEqual(deployed.returncode, 0, deployed.stderr)
                self.assertEqual(deployed.stdout.strip(), "True")


if __name__ == "__main__":
    unittest.main()
