"""Regression tests for startup-time authentication configuration validation."""
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


BACKEND_DIRECTORY = Path(__file__).resolve().parent


class SecretKeyConfigurationTests(unittest.TestCase):
    def import_backend(self, **environment):
        process_environment = os.environ.copy()
        process_environment.pop("APP_ENV", None)
        process_environment.pop("SECRET_KEY", None)
        process_environment.update(environment)
        process_environment["PYTHONPATH"] = str(BACKEND_DIRECTORY)

        with tempfile.TemporaryDirectory() as directory:
            return subprocess.run(
                [sys.executable, "-c", "import main; print(main.SECRET_KEY)"],
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

    def test_explicit_development_allows_the_local_key(self):
        result = self.import_backend(APP_ENV="development")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout.strip(), "dev-secret-key-change-in-production")


if __name__ == "__main__":
    unittest.main()
