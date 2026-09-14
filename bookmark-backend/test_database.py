"""Tests for database engine configuration."""

import unittest

from database import engine_options


class DatabaseEngineConfigurationTests(unittest.TestCase):
    def test_sqlite_disables_same_thread_check(self):
        for database_url in (
            "sqlite:///./bookmarks.db",
            "sqlite+pysqlite:////var/lib/bookmarks-app/bookmarks.db",
        ):
            with self.subTest(database_url=database_url):
                self.assertEqual(
                    engine_options(database_url),
                    {"connect_args": {"check_same_thread": False}},
                )

    def test_external_dialects_do_not_receive_sqlite_options(self):
        for database_url in (
            "postgresql+psycopg://user:password@database/bookmarks",
            "mysql+pymysql://user:password@database/bookmarks",
        ):
            with self.subTest(database_url=database_url):
                self.assertEqual(engine_options(database_url), {})


if __name__ == "__main__":
    unittest.main()
