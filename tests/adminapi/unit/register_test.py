from contextlib import contextmanager

import bcrypt
import pytest
from psycopg import sql

from app.adminapi.domain.auth import AuthManager
from app.lib import auth, mock
from app.lib.web.errors import ConflictError
from app.specs import adminapi


@pytest.fixture
def manager() -> tuple[AuthManager, mock.MagicMock]:
    storage = mock.MagicMock()
    auth_manager = AuthManager(auth.NoopAuthenticator(), storage)
    auth_manager.with_tx = mock.MagicMock(return_value=_null_context())
    return auth_manager, storage


def test_register_conflict_on_existing_login(manager: tuple[AuthManager, mock.MagicMock]) -> None:
    auth_manager, storage = manager
    storage.query.side_effect = [
        [{"login": "taken", "email": "other@example.com"}],
    ]

    with pytest.raises(ConflictError) as ctx:
        auth_manager.register(adminapi.RegisterRequest(username="taken", email="new@example.com", password="secret"))

    assert str(ctx.value.message()) == "user 'taken' already exists"
    storage.exec.assert_not_called()


def test_register_conflict_on_existing_email(manager: tuple[AuthManager, mock.MagicMock]) -> None:
    auth_manager, storage = manager
    storage.query.side_effect = [
        [{"login": "other", "email": "taken@example.com"}],
    ]

    with pytest.raises(ConflictError) as ctx:
        auth_manager.register(
            adminapi.RegisterRequest(username="newuser", email="taken@example.com", password="secret")
        )

    assert str(ctx.value.message()) == "email 'taken@example.com' already exists"
    storage.exec.assert_not_called()


def test_register_conflict_on_existing_db_role(manager: tuple[AuthManager, mock.MagicMock]) -> None:
    auth_manager, storage = manager
    storage.query.side_effect = [
        [],
        [{"?column?": 1}],
    ]

    with pytest.raises(ConflictError) as ctx:
        auth_manager.register(
            adminapi.RegisterRequest(username="dbrole", email="dbrole@example.com", password="secret")
        )

    assert str(ctx.value.message()) == "database user 'dbrole' already exists"
    storage.exec.assert_not_called()


def test_register_creates_backend_and_db_user(manager: tuple[AuthManager, mock.MagicMock]) -> None:
    auth_manager, storage = manager
    storage.query.side_effect = [[], []]

    response = auth_manager.register(
        adminapi.RegisterRequest(username="newuser", email="new@example.com", password="secret")
    )

    assert isinstance(response, adminapi.RegisterResponse)
    assert len(storage.exec.call_args_list) == 3

    insert_call = storage.exec.call_args_list[0]
    assert "INSERT INTO private.users" in insert_call.args[0]
    insert_params = insert_call.kwargs["params"]
    assert insert_params[:3] == ["newuser", "newuser", "new@example.com"]
    assert bcrypt.checkpw(b"secret", insert_params[3])

    create_role_arg = storage.exec.call_args_list[1].args[0]
    assert isinstance(create_role_arg, sql.Composed)

    grant_arg = storage.exec.call_args_list[2].args[0]
    assert isinstance(grant_arg, sql.Composed)


@contextmanager
def _null_context():
    yield
