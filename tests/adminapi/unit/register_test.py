import unittest
from contextlib import contextmanager
from unittest import mock

import bcrypt
from psycopg import sql

from app.adminapi import presentation as adminapi
from app.adminapi.domain.login import LoginManager
from app.lib import auth
from app.lib.web.errors import ConflictError


class LoginManagerRegisterTest(unittest.TestCase):
    def setUp(self) -> None:
        self.storage = mock.MagicMock()
        self.manager = LoginManager(auth.NoopAuthenticator(), self.storage)
        self.manager.with_tx = mock.MagicMock(return_value=_null_context())

    def test_register_conflict_on_existing_login(self) -> None:
        self.storage.query.side_effect = [
            [{"login": "taken", "email": "other@example.com"}],
        ]

        with self.assertRaises(ConflictError) as ctx:
            self.manager.register(
                adminapi.RegisterRequest(username="taken", email="new@example.com", password="secret")
            )

        self.assertEqual(str(ctx.exception.message()), "user 'taken' already exists")
        self.storage.exec.assert_not_called()

    def test_register_conflict_on_existing_email(self) -> None:
        self.storage.query.side_effect = [
            [{"login": "other", "email": "taken@example.com"}],
        ]

        with self.assertRaises(ConflictError) as ctx:
            self.manager.register(
                adminapi.RegisterRequest(username="newuser", email="taken@example.com", password="secret")
            )

        self.assertEqual(str(ctx.exception.message()), "email 'taken@example.com' already exists")
        self.storage.exec.assert_not_called()

    def test_register_conflict_on_existing_db_role(self) -> None:
        self.storage.query.side_effect = [
            [],
            [{"?column?": 1}],
        ]

        with self.assertRaises(ConflictError) as ctx:
            self.manager.register(
                adminapi.RegisterRequest(username="dbrole", email="dbrole@example.com", password="secret")
            )

        self.assertEqual(str(ctx.exception.message()), "database user 'dbrole' already exists")
        self.storage.exec.assert_not_called()

    def test_register_creates_backend_and_db_user(self) -> None:
        self.storage.query.side_effect = [[], []]

        response = self.manager.register(
            adminapi.RegisterRequest(username="newuser", email="new@example.com", password="secret")
        )

        self.assertIsInstance(response, adminapi.RegisterResponse)
        self.assertEqual(self.storage.exec.call_count, 3)

        insert_call = self.storage.exec.call_args_list[0]
        self.assertIn("INSERT INTO private.users", insert_call.args[0])
        insert_params = insert_call.kwargs["params"]
        self.assertEqual(insert_params[:3], ["newuser", "newuser", "new@example.com"])
        self.assertTrue(bcrypt.checkpw(b"secret", insert_params[3]))

        create_role_arg = self.storage.exec.call_args_list[1].args[0]
        self.assertIsInstance(create_role_arg, sql.Composed)

        grant_arg = self.storage.exec.call_args_list[2].args[0]
        self.assertIsInstance(grant_arg, sql.Composed)


@contextmanager
def _null_context():
    yield
