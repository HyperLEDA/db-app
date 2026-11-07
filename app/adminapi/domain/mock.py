from unittest import mock

from app.adminapi import clients
from app.adminapi.domain import actions
from app.lib import auth


def get_mock_actions():
    return actions.Actions(
        repo=mock.MagicMock(),
        authenticator=auth.NoopAuthenticator(),
        storage=mock.MagicMock(),
        clients=clients.get_mock_clients(),
    )
