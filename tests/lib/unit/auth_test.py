import hashlib

import bcrypt
import pytest

from app.lib import auth, mock
from tests.lib import mocks


@pytest.fixture
def mock_storage() -> mock.MagicMock:
    return mock.MagicMock()


@pytest.fixture
def authenticator(mock_storage: mock.MagicMock) -> auth.PostgresAuthenticator:
    return auth.PostgresAuthenticator(mock_storage)


def test_login_correct_password(
    mock_storage: mock.MagicMock,
    authenticator: auth.PostgresAuthenticator,
) -> None:
    with mock.patch("secrets.token_hex", return_value="123456789"):
        mocks.returns(
            mock_storage.query_one,
            {
                "password_hash": bcrypt.hashpw(b"password", bcrypt.gensalt()),
                "id": 1,
            },
        )
        assert authenticator.login("username", "password") == ("123456789", True)
        mock_storage.exec.assert_called_once()
        inserted_hash = mock_storage.exec.call_args.kwargs["params"][0]
        assert isinstance(inserted_hash, bytes)
        assert inserted_hash == hashlib.sha256(b"123456789").digest()


def test_login_user_does_not_exist(
    mock_storage: mock.MagicMock,
    authenticator: auth.PostgresAuthenticator,
) -> None:
    mock_storage.query_one.side_effect = RuntimeError()
    assert authenticator.login("username", "password") == ("", False)


def test_login_user_does_not_exist_still_checks_password_hash(
    mock_storage: mock.MagicMock,
    authenticator: auth.PostgresAuthenticator,
) -> None:
    with mock.patch("bcrypt.checkpw", return_value=False) as checkpw_mock:
        mock_storage.query_one.side_effect = RuntimeError()
        assert authenticator.login("username", "password") == ("", False)
        checkpw_mock.assert_called_once()


def test_login_wrong_password(
    mock_storage: mock.MagicMock,
    authenticator: auth.PostgresAuthenticator,
) -> None:
    mocks.returns(mock_storage.query_one, {"password_hash": bcrypt.hashpw(b"password", bcrypt.gensalt())})
    assert authenticator.login("username", "wrong_password") == ("", False)


def test_authenticate_invalid_token(
    mock_storage: mock.MagicMock,
    authenticator: auth.PostgresAuthenticator,
) -> None:
    mock_storage.query_one.side_effect = RuntimeError()
    assert authenticator.authenticate("non_existent_token") == (None, False)


def test_authenticate_correct_token(
    mock_storage: mock.MagicMock,
    authenticator: auth.PostgresAuthenticator,
) -> None:
    mocks.returns(
        mock_storage.query_one,
        {
            "user_id": 1,
            "role": auth.Role.ADMIN,
            "login": "admin",
        },
    )

    user, is_authenticated = authenticator.authenticate("correct_token")
    assert is_authenticated
    assert user == auth.User(1, auth.Role.ADMIN, "admin")


def test_authenticate_hashes_incoming_token(
    mock_storage: mock.MagicMock,
    authenticator: auth.PostgresAuthenticator,
) -> None:
    mocks.returns(
        mock_storage.query_one,
        {"user_id": 1, "role": auth.Role.ADMIN, "login": "admin"},
    )
    authenticator.authenticate("mytoken")
    passed_hash = mock_storage.query_one.call_args.kwargs["params"][0]
    assert passed_hash == hashlib.sha256(b"mytoken").digest()
