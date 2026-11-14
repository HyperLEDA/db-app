from unittest import mock

from app.adminapi import clients
from app.adminapi.domain import actions


def get_mock_actions():
    return actions.Actions(
        repo=mock.MagicMock(),
        clients=clients.get_mock_clients(),
    )
