from unittest import mock

from app.domain.adminapi import actions
from app.lib import auth, clients


def get_mock_actions():
    c = clients.Clients(ads_token="test")
    c.ads = mock.MagicMock()
    c.vizier = mock.MagicMock()

    return actions.Actions(
        common_repo=mock.MagicMock(),
        layer0_repo=mock.MagicMock(),
        layer1_repo=mock.MagicMock(),
        layer2_repo=mock.MagicMock(),
        authenticator=auth.NoopAuthenticator(),
        clients=c,
    )
