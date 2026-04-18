import hashlib
import unittest
from unittest import mock

import bcrypt

from app.lib import auth
from tests import lib


class PostgresAuthenticatorTest(unittest.TestCase):
    def setUp(self):
        self.mock_storage = mock.MagicMock()
        self.authenticator = auth.PostgresAuthenticator(self.mock_storage)

    @mock.patch("secrets.token_hex", return_value="123456789")
    def test_login_correct_password(self, _):
        lib.returns(
            self.mock_storage.query_one,
            {
                "password_hash": bcrypt.hashpw(b"password", bcrypt.gensalt()),
                "id": 1,
            },
        )
        self.assertEqual(("123456789", True), self.authenticator.login("username", "password"))
        self.mock_storage.exec.assert_called_once()
        inserted_hash = self.mock_storage.exec.call_args.kwargs["params"][0]
        self.assertIsInstance(inserted_hash, bytes)
        self.assertEqual(inserted_hash, hashlib.sha256(b"123456789").digest())

    def test_login_user_does_not_exist(self):
        lib.raises(self.mock_storage.query_one, RuntimeError)
        self.assertEqual(("", False), self.authenticator.login("username", "password"))

    @mock.patch("bcrypt.checkpw", return_value=False)
    def test_login_user_does_not_exist_still_checks_password_hash(self, checkpw_mock):
        lib.raises(self.mock_storage.query_one, RuntimeError)
        self.assertEqual(("", False), self.authenticator.login("username", "password"))
        checkpw_mock.assert_called_once()

    def test_login_wrong_password(self):
        lib.returns(self.mock_storage.query_one, {"password_hash": bcrypt.hashpw(b"password", bcrypt.gensalt())})
        self.assertEqual(("", False), self.authenticator.login("username", "wrong_password"))

    def test_authenticate_invalid_token(self):
        lib.raises(self.mock_storage.query_one, RuntimeError)
        self.assertEqual((None, False), self.authenticator.authenticate("non_existent_token"))

    def test_authenticate_correct_token(self):
        lib.returns(
            self.mock_storage.query_one,
            {
                "user_id": 1,
                "role": auth.Role.ADMIN,
            },
        )

        user, is_authenticated = self.authenticator.authenticate("correct_token")
        self.assertTrue(is_authenticated)
        self.assertEqual(user, auth.User(1, auth.Role.ADMIN))

    def test_authenticate_hashes_incoming_token(self):
        lib.returns(
            self.mock_storage.query_one,
            {"user_id": 1, "role": auth.Role.ADMIN},
        )
        self.authenticator.authenticate("mytoken")
        passed_hash = self.mock_storage.query_one.call_args.kwargs["params"][0]
        self.assertEqual(passed_hash, hashlib.sha256(b"mytoken").digest())
