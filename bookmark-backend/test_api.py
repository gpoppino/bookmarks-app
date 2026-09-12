"""Integration tests for user authentication and bookmark CRUD."""
import importlib.util
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

from fastapi.testclient import TestClient


BACKEND_MODULE = Path(__file__).resolve().with_name("main.py")


class AuthenticationAndBookmarkIntegrationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.directory = tempfile.TemporaryDirectory()
        cls.module_name = "bookmarks_api_integration_tests"
        previous = Path.cwd()
        try:
            os.chdir(cls.directory.name)
            spec = importlib.util.spec_from_file_location(
                cls.module_name, BACKEND_MODULE
            )
            cls.api = importlib.util.module_from_spec(spec)
            sys.modules[cls.module_name] = cls.api
            with patch.dict(os.environ, {"APP_ENV": "development"}):
                spec.loader.exec_module(cls.api)
            # Pin the SQLite connection to the disposable working directory.
            cls.api.engine.connect().close()
        finally:
            os.chdir(previous)

    @classmethod
    def tearDownClass(cls):
        cls.api.engine.dispose()
        sys.modules.pop(cls.module_name, None)
        cls.directory.cleanup()

    def setUp(self):
        self.api.Base.metadata.drop_all(self.api.engine)
        self.api.Base.metadata.create_all(self.api.engine)
        self.client = TestClient(self.api.app)
        self.metadata = patch.object(
            self.api,
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

    def register(self, username, password="password-123"):
        return self.client.post(
            "/api/auth/register",
            json={"username": username, "password": password},
        )

    def login(self, username, password="password-123"):
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
            json={"current_password": "wrong", "new_password": "new-password"},
        )
        self.assertEqual(wrong.status_code, 400, wrong.text)

        changed = self.client.put(
            "/api/auth/password",
            json={
                "current_password": "password-123",
                "new_password": "new-password",
            },
        )
        self.assertEqual(changed.status_code, 200, changed.text)

        self.client.cookies.clear()
        self.assertEqual(self.login("alice").status_code, 401)
        self.assertEqual(self.login("alice", "new-password").status_code, 200)
        self.assertEqual(self.client.get("/api/auth/me").status_code, 200)

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
