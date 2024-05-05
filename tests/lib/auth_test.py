import unittest
from datetime import datetime, timedelta, timezone
from unittest import mock

import bcrypt

from app.lib import auth


class PostgresAuthenticatorTest(unittest.TestCase):
    def setUp(self):
        self.mock_storage = mock.MagicMock()
        self.authenticator = auth.PostgresAuthenticator(self.mock_storage)

    @mock.patch("secrets.token_hex", return_value="123456789")
    def test_login_correct_password(self, _):
        self.mock_storage.query_one.return_value = {
            "password_hash": bcrypt.hashpw(b"password", bcrypt.gensalt()),
            "id": 1,
        }
        self.assertEqual(("123456789", True), self.authenticator.login("username", "password"))

    def test_login_user_does_not_exist(self):
        self.mock_storage.query_one.side_effect = RuntimeError
        self.assertEqual(("", False), self.authenticator.login("username", "password"))

    def test_login_wrong_password(self):
        self.mock_storage.query_one.return_value = {"password_hash": bcrypt.hashpw(b"password", bcrypt.gensalt())}
        self.assertEqual(("", False), self.authenticator.login("username", "wrong_password"))

    def test_authenticate_invalid_token(self):
        self.mock_storage.query_one.side_effect = RuntimeError
        self.assertEqual((None, False), self.authenticator.authenticate("non_existent_token"))

    def test_authenticate_correct_token(self):
        self.mock_storage.query_one.return_value = {
            "expiry_time": datetime.now(timezone.utc) + timedelta(days=1),
            "active": True,
            "user_id": 1,
            "role": auth.user.Role.ADMIN,
        }

        user, is_authenticated = self.authenticator.authenticate("correct_token")
        self.assertTrue(is_authenticated)
        self.assertEqual(user, auth.user.User(1, auth.user.Role.ADMIN))
