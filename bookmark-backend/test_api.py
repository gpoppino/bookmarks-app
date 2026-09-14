"""Integration tests for user authentication and bookmark CRUD."""
import importlib
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import Mock, patch

from fastapi.testclient import TestClient


BACKEND_MODULE_NAMES = (
    "main", "auth_routes", "bookmark_routes", "bookmark_service", "auth",
    "config", "database", "metadata", "models", "password_policy", "schemas",
)


class AuthenticationAndBookmarkIntegrationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.directory = tempfile.TemporaryDirectory()
        previous = Path.cwd()
        try:
            os.chdir(cls.directory.name)
            for module_name in BACKEND_MODULE_NAMES:
                sys.modules.pop(module_name, None)
            with patch.dict(os.environ, {"APP_ENV": "development"}):
                cls.api = importlib.import_module("main")
            # Pin the SQLite connection to the disposable working directory.
            cls.api.engine.connect().close()
        finally:
            os.chdir(previous)

    @classmethod
    def tearDownClass(cls):
        cls.api.engine.dispose()
        for module_name in BACKEND_MODULE_NAMES:
            sys.modules.pop(module_name, None)
        cls.directory.cleanup()

    def setUp(self):
        self.api.Base.metadata.drop_all(self.api.engine)
        self.api.Base.metadata.create_all(self.api.engine)
        self.client = TestClient(self.api.app)
        self.metadata = patch.object(
            self.api.bookmark_routes,
            "fetch_bookmark_metadata",
            side_effect=lambda url: {
                "success": True,
                "url": url,
                "title": f"Title for {url}",
                "description": f"Description for {url}",
            },
        )
        self.metadata.start()
        self.addCleanup(self.metadata.stop)
        self.addCleanup(self.client.close)

    def register(self, username, password="password-123456"):
        return self.client.post(
            "/api/auth/register",
            json={"username": username, "password": password},
        )

    def login(self, username, password="password-123456"):
        return self.client.post(
            "/api/auth/login",
            json={"username": username, "password": password},
        )

    def create_bookmark(self, url="https://example.test", tags=None):
        return self.client.post(
            "/api/bookmarks",
            json={"url": url, "tags": tags or []},
        )

    def test_register_login_me_and_logout_flow(self):
        self.assertEqual(self.client.get("/api/auth/me").status_code, 401)

        registration = self.register("alice")
        self.assertEqual(registration.status_code, 201, registration.text)
        self.assertEqual(registration.json()["username"], "alice")
        self.assertEqual(self.register("alice").status_code, 409)

        self.assertEqual(self.login("unknown").status_code, 401)
        self.assertEqual(self.login("alice", "wrong-password").status_code, 401)

        login = self.login("alice")
        self.assertEqual(login.status_code, 200, login.text)
        profile = self.client.get("/api/auth/me")
        self.assertEqual(profile.status_code, 200, profile.text)
        self.assertEqual(profile.json()["username"], "alice")

        logout = self.client.post("/api/auth/logout")
        self.assertEqual(logout.status_code, 200, logout.text)
        self.assertEqual(logout.json(), {"success": True})
        self.assertEqual(self.client.get("/api/auth/me").status_code, 401)

    def test_password_change_rejects_wrong_current_password_and_rotates_login(self):
        self.assertEqual(self.register("alice").status_code, 201)
        self.assertEqual(self.login("alice").status_code, 200)

        wrong = self.client.put(
            "/api/auth/password",
            json={"current_password": "wrong", "new_password": "new-password-123"},
        )
        self.assertEqual(wrong.status_code, 400, wrong.text)

        changed = self.client.put(
            "/api/auth/password",
            json={
                "current_password": "password-123456",
                "new_password": "new-password-123",
            },
        )
        self.assertEqual(changed.status_code, 200, changed.text)

        self.client.cookies.clear()
        self.assertEqual(self.login("alice").status_code, 401)
        self.assertEqual(self.login("alice", "new-password-123").status_code, 200)
        self.assertEqual(self.client.get("/api/auth/me").status_code, 200)

    def test_registration_rejects_passwords_outside_the_policy(self):
        cases = (
            ("short", "at least 15 characters"),
            (" " * 15, "only of whitespace"),
            ("valid-password\n", "control characters"),
            ("é" * 37, "72 UTF-8 bytes"),
        )
        for index, (password, expected_error) in enumerate(cases):
            with self.subTest(expected_error=expected_error):
                response = self.register(f"rejected-{index}", password)
                self.assertEqual(response.status_code, 400, response.text)
                self.assertIn(expected_error, response.json()["detail"])

        accepted = self.register("passphrase-user", "correct horse battery staple")
        self.assertEqual(accepted.status_code, 201, accepted.text)

    def test_password_change_enforces_policy_and_preserves_old_password(self):
        self.assertEqual(self.register("alice").status_code, 201)
        self.assertEqual(self.login("alice").status_code, 200)

        rejected = self.client.put(
            "/api/auth/password",
            json={"current_password": "password-123456", "new_password": "too-short"},
        )
        self.assertEqual(rejected.status_code, 400, rejected.text)
        self.assertIn("at least 15 characters", rejected.json()["detail"])

        self.client.cookies.clear()
        self.assertEqual(self.login("alice", "password-123456").status_code, 200)

    def test_bookmark_create_list_update_delete_flow(self):
        self.assertEqual(self.register("alice").status_code, 201)
        self.assertEqual(self.login("alice").status_code, 200)

        created = self.create_bookmark(
            "https://first.test", [" Python ", "API"]
        )
        self.assertEqual(created.status_code, 201, created.text)
        bookmark = created.json()
        self.assertEqual(bookmark["url"], "https://first.test")
        self.assertEqual(set(bookmark["tags"]), {"python", "api"})

        listing = self.client.get("/api/bookmarks")
        self.assertEqual(listing.status_code, 200, listing.text)
        self.assertEqual([item["id"] for item in listing.json()], [bookmark["id"]])

        updated = self.client.put(
            f"/api/bookmarks/{bookmark['id']}",
            json={"url": "https://updated.test", "tags": ["Updated"]},
        )
        self.assertEqual(updated.status_code, 200, updated.text)
        self.assertEqual(updated.json()["url"], "https://updated.test")
        self.assertEqual(updated.json()["title"], "Title for https://updated.test")
        self.assertEqual(updated.json()["tags"], ["updated"])

        deleted = self.client.delete(f"/api/bookmarks/{bookmark['id']}")
        self.assertEqual(deleted.status_code, 200, deleted.text)
        self.assertEqual(self.client.get("/api/bookmarks").json(), [])
        self.assertEqual(
            self.client.delete(f"/api/bookmarks/{bookmark['id']}").status_code,
            404,
        )

    def test_automatic_tags_merge_with_manual_tags_and_reuse_user_vocabulary(self):
        self.assertEqual(self.register("alice").status_code, 201)
        self.assertEqual(self.login("alice").status_code, 200)
        self.assertEqual(
            self.create_bookmark(
                "https://existing.test", ["python", "fastapi"]
            ).status_code,
            201,
        )

        suggester = Mock(enabled=True)
        suggester.suggest.return_value = [
            "new-one",
            "#Python",
            "new-two",
            "new-three",
            "FastAPI",
        ]
        with patch.object(self.api.bookmark_service, "tag_suggester", suggester):
            created = self.create_bookmark(
                "https://automatic.test", ["manual", "python"]
            )

        self.assertEqual(created.status_code, 201, created.text)
        self.assertEqual(
            created.json()["tags"],
            ["manual", "python", "fastapi", "new-one", "new-two"],
        )
        context = suggester.suggest.call_args.args[0]
        self.assertEqual(context.domain, "automatic.test")
        self.assertEqual(context.existing_tags, ("fastapi", "python"))

    def test_automatic_tagging_failure_does_not_fail_bookmark_creation(self):
        self.assertEqual(self.register("alice").status_code, 201)
        self.assertEqual(self.login("alice").status_code, 200)
        suggester = Mock(enabled=True)
        suggester.suggest.side_effect = TimeoutError("provider timeout")

        with patch.object(self.api.bookmark_service, "tag_suggester", suggester):
            created = self.create_bookmark(tags=["manual"])

        self.assertEqual(created.status_code, 201, created.text)
        self.assertEqual(created.json()["tags"], ["manual"])

    def test_only_the_current_users_tag_vocabulary_is_sent(self):
        self.assertEqual(self.register("alice").status_code, 201)
        self.assertEqual(self.login("alice").status_code, 200)
        self.assertEqual(
            self.create_bookmark(tags=["alice-private"]).status_code,
            201,
        )
        self.client.cookies.clear()
        self.assertEqual(self.register("bob").status_code, 201)
        self.assertEqual(self.login("bob").status_code, 200)

        suggester = Mock(enabled=True)
        suggester.suggest.return_value = []
        with patch.object(self.api.bookmark_service, "tag_suggester", suggester):
            created = self.create_bookmark("https://bob.test")

        self.assertEqual(created.status_code, 201, created.text)
        context = suggester.suggest.call_args.args[0]
        self.assertEqual(context.existing_tags, ())

    def test_duplicate_bookmark_is_rejected_per_user(self):
        self.assertEqual(self.register("alice").status_code, 201)
        self.assertEqual(self.login("alice").status_code, 200)
        self.assertEqual(self.create_bookmark().status_code, 201)

        duplicate = self.create_bookmark()
        self.assertEqual(duplicate.status_code, 400, duplicate.text)
        self.assertEqual(duplicate.json()["detail"], "Bookmark already exists")
        self.assertEqual(len(self.client.get("/api/bookmarks").json()), 1)

    def test_bookmarks_are_isolated_between_users(self):
        self.assertEqual(self.register("alice").status_code, 201)
        self.assertEqual(self.login("alice").status_code, 200)
        alice_bookmark = self.create_bookmark(tags=["alice-only"]).json()

        self.client.cookies.clear()
        self.assertEqual(self.register("bob").status_code, 201)
        self.assertEqual(self.login("bob").status_code, 200)
        self.assertEqual(self.client.get("/api/bookmarks").json(), [])
        self.assertEqual(self.client.get("/api/tags").json(), [])

        bookmark_path = f"/api/bookmarks/{alice_bookmark['id']}"
        self.assertEqual(
            self.client.put(bookmark_path, json={"tags": ["stolen"]}).status_code,
            404,
        )
        self.assertEqual(self.client.delete(bookmark_path).status_code, 404)

        bob_bookmark = self.create_bookmark(tags=["bob-only"])
        self.assertEqual(bob_bookmark.status_code, 201, bob_bookmark.text)
        self.assertNotEqual(bob_bookmark.json()["id"], alice_bookmark["id"])
        self.assertEqual(
            [item["id"] for item in self.client.get("/api/bookmarks").json()],
            [bob_bookmark.json()["id"]],
        )
        self.assertEqual(
            [tag["name"] for tag in self.client.get("/api/tags").json()],
            ["bob-only"],
        )

        self.client.cookies.clear()
        self.assertEqual(self.login("alice").status_code, 200)
        self.assertEqual(
            [item["id"] for item in self.client.get("/api/bookmarks").json()],
            [alice_bookmark["id"]],
        )

    def test_session_is_required_for_user_and_bookmark_routes(self):
        requests = [
            ("get", "/api/auth/me", None),
            (
                "put",
                "/api/auth/password",
                {"current_password": "old", "new_password": "new"},
            ),
            ("get", "/api/bookmarks", None),
            ("post", "/api/bookmarks", {"url": "https://example.test"}),
            ("put", "/api/bookmarks/1", {"tags": ["blocked"]}),
            ("delete", "/api/bookmarks/1", None),
            ("get", "/api/tags", None),
        ]
        for method, path, body in requests:
            with self.subTest(method=method, path=path):
                response = self.client.request(method, path, json=body)
                self.assertEqual(response.status_code, 401, response.text)


if __name__ == "__main__":
    unittest.main()
