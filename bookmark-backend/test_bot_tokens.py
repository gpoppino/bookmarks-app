"""Run with python -m unittest -v test_bot_tokens (uses only a temporary DB)."""
import importlib
import os
from pathlib import Path
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from unittest.mock import patch

from fastapi.testclient import TestClient


class BotTokenTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.directory = tempfile.TemporaryDirectory()
        previous = Path.cwd()
        try:
            os.chdir(cls.directory.name)
            cls.api = importlib.import_module("main")
            # Connect while cwd still points at the disposable database directory.
            cls.api.engine.connect().close()
        finally:
            os.chdir(previous)

    @classmethod
    def tearDownClass(cls):
        cls.api.engine.dispose()
        cls.directory.cleanup()

    def setUp(self):
        self.api.Base.metadata.drop_all(self.api.engine)
        self.api.Base.metadata.create_all(self.api.engine)
        with self.api.SessionLocal() as db:
            db.add_all([self.api.UserDB(username=name, hashed_password="unused")
                        for name in ("alice", "bob")])
            db.commit()
        self.client = TestClient(self.api.app)
        self.session("alice")
        self.metadata = patch.object(self.api, "fetch_bookmark_metadata",
                                     side_effect=lambda url: {
                                         "success": True, "url": url,
                                         "title": "Test", "description": "Test"})
        self.metadata.start()
        self.addCleanup(self.metadata.stop)
        self.addCleanup(self.client.close)

    def session(self, username, expired=False):
        self.client.cookies.clear()
        token = self.api.create_access_token({"sub": username},
                    timedelta(days=-1 if expired else 1))
        self.client.cookies.set("access_token", token)

    def mint(self, **options):
        response = self.client.post("/api/auth/bot-tokens",
                                    json={"name": "Pi", **options})
        self.assertEqual(response.status_code, 201, response.text)
        return response

    def save(self, token, url="https://example.dev", cookie=False):
        self.client.cookies.clear()
        headers = {}
        if cookie:
            self.client.cookies.set("access_token", token)
        else:
            headers["Authorization"] = "Bearer " + token
        return self.client.post("/api/bookmarks", json={"url": url}, headers=headers)

    def test_creation_stores_only_hash_and_lists_only_metadata(self):
        response = self.mint(name="  Pi  ")
        data = response.json()
        token = data["token"]
        self.assertEqual(len(token), 47)
        self.assertTrue(token.startswith("bkt_"))
        self.assertEqual(data["name"], "Pi")
        self.assertEqual(data["scope"], "bookmarks:create")
        self.assertIsNone(data["expires_at"])
        self.assertEqual(response.headers["cache-control"], "no-store")
        with self.api.SessionLocal() as db:
            record = db.query(self.api.BotTokenDB).one()
            self.assertEqual(record.token_hash, self.api.hash_bot_token(token))
            self.assertNotEqual(record.token_hash, token)
        listing = self.client.get("/api/auth/bot-tokens")
        self.assertNotIn(token, listing.text)
        self.assertNotIn("token_hash", listing.text)
        self.assertNotIn("token", listing.json()[0])
        self.assertEqual(listing.headers["cache-control"], "no-store")

    def test_bearer_and_legacy_cookie_save_under_owner(self):
        token = self.mint().json()["token"]
        self.assertEqual(self.save(token).status_code, 201)
        self.assertEqual(self.save(token, "https://second.dev", cookie=True).status_code, 201)
        with self.api.SessionLocal() as db:
            alice = db.query(self.api.UserDB).filter_by(username="alice").one()
            self.assertEqual({b.user_id for b in db.query(self.api.BookmarkDB)}, {alice.id})
            self.assertIsNotNone(db.query(self.api.BotTokenDB).one().last_used_at)
        self.session("bob")
        self.assertEqual(self.client.get("/api/bookmarks").json(), [])

    def test_revocation_blocks_both_transports_immediately(self):
        data = self.mint().json()
        self.assertEqual(self.save(data["token"]).status_code, 201)
        self.session("alice")
        path = "/api/auth/bot-tokens/" + str(data["id"])
        self.assertEqual(self.client.delete(path).status_code, 204)
        self.assertEqual(self.client.delete(path).status_code, 204)
        self.assertIsNotNone(self.client.get("/api/auth/bot-tokens").json()[0]["revoked_at"])
        for cookie in (False, True):
            self.assertEqual(self.save(data["token"], cookie=cookie).status_code, 401)

    def test_users_cannot_list_or_revoke_each_others_tokens(self):
        data = self.mint().json()
        self.session("bob")
        self.assertEqual(self.client.get("/api/auth/bot-tokens").json(), [])
        self.assertEqual(self.client.delete(
            "/api/auth/bot-tokens/" + str(data["id"])).status_code, 404)
        self.assertEqual(self.save(data["token"]).status_code, 201)

    def test_bot_cannot_read_delete_or_manage_account(self):
        data = self.mint().json()
        endpoints = [("get", "/api/bookmarks", None),
                     ("get", "/api/tags", None),
                     ("get", "/api/auth/me", None),
                     ("get", "/api/auth/bot-tokens", None),
                     ("post", "/api/auth/bot-tokens", {"name": "escalation"}),
                     ("delete", "/api/auth/bot-tokens/1", None),
                     ("put", "/api/auth/password", {"current_password": "x", "new_password": "y"}),
                     ("put", "/api/bookmarks/1", {"url": "https://changed.dev"}),
                     ("delete", "/api/bookmarks/1", None)]
        for cookie in (False, True):
            self.client.cookies.clear()
            headers = {}
            if cookie:
                self.client.cookies.set("access_token", data["token"])
            else:
                headers["Authorization"] = "Bearer " + data["token"]
            for method, path, body in endpoints:
                with self.subTest(cookie=cookie, path=path, method=method):
                    response = self.client.request(method, path, json=body, headers=headers)
                    self.assertEqual(response.status_code, 401, response.text)

    def test_invalid_bearer_does_not_fall_back_to_valid_session(self):
        for value in ("Bearer invalid", "Basic abc", "Bearer", ""):
            self.assertEqual(self.client.post("/api/bookmarks",
                json={"url": "https://example.dev"},
                headers={"Authorization": value}).status_code, 401)
        self.assertEqual(self.client.post("/api/auth/bot-tokens", json={"name": "x"},
            headers={"Authorization": "Bearer invalid"}).status_code, 401)

    def test_optional_expiry_and_deleted_owner(self):
        data = self.mint(expires_in_days=1).json()
        self.assertIsNotNone(data["expires_at"])
        with self.api.SessionLocal() as db:
            db.query(self.api.BotTokenDB).one().expires_at = datetime.now(timezone.utc) - timedelta(seconds=1)
            db.commit()
        self.assertEqual(self.save(data["token"]).status_code, 401)
        self.session("bob")
        token = self.mint().json()["token"]
        with self.api.SessionLocal() as db:
            db.delete(db.query(self.api.UserDB).filter_by(username="bob").one())
            db.commit()
        self.assertEqual(self.save(token).status_code, 401)

    def test_session_and_signing_key_expiry_do_not_expire_bot_token(self):
        token = self.mint().json()["token"]
        self.session("alice", expired=True)
        self.assertEqual(self.client.post("/api/auth/bot-tokens", json={"name": "x"}).status_code, 401)
        self.api.engine.dispose()
        with patch.object(self.api, "SECRET_KEY", "rotated-key"):
            self.assertEqual(self.save(token).status_code, 201)

    def test_existing_session_can_still_save(self):
        self.assertEqual(self.client.post("/api/bookmarks",
            json={"url": "https://example.dev"}).status_code, 201)

    def test_validation_and_unique_tokens(self):
        for body in ({"name": " "}, {"name": "x" * 101},
                     {"name": "x", "expires_in_days": 0},
                     {"name": "x", "expires_in_days": 3651}):
            self.assertEqual(self.client.post("/api/auth/bot-tokens", json=body).status_code, 422)
        self.assertNotEqual(self.mint().json()["token"], self.mint().json()["token"])

    def test_additive_table_creation_preserves_existing_users(self):
        self.api.BotTokenDB.__table__.drop(self.api.engine)
        self.api.Base.metadata.create_all(self.api.engine)
        self.api.Base.metadata.create_all(self.api.engine)
        with self.api.SessionLocal() as db:
            self.assertEqual(db.query(self.api.UserDB).count(), 2)
        self.mint()

    def test_unauthenticated_and_unknown_tokens_are_rejected(self):
        self.client.cookies.clear()
        self.assertEqual(self.client.get("/api/auth/bot-tokens").status_code, 401)
        self.assertEqual(self.client.post("/api/auth/bot-tokens", json={"name": "x"}).status_code, 401)
        self.assertEqual(self.save("bkt_" + "x" * 43).status_code, 401)


if __name__ == "__main__":
    unittest.main()
