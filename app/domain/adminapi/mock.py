from unittest import mock

from app.data import model
from app.domain.adminapi import CacheRegistry, actions
from app.lib import auth, clients


def get_mock_actions():
    c = clients.Clients(ads_token="test")
    c.ads = mock.MagicMock()
    c.vizier = mock.MagicMock()

    cache_mock = mock.MagicMock()
    cache_mock.get.return_value = model.RawdataTableRowCounts(rows_by_table={})
    cache_registry = CacheRegistry(rawdata_row_counts=cache_mock)

    return actions.Actions(
        common_repo=mock.MagicMock(),
        layer0_repo=mock.MagicMock(),
        layer1_repo=mock.MagicMock(),
        layer2_repo=mock.MagicMock(),
        authenticator=auth.NoopAuthenticator(),
        clients=c,
        cache_registry=cache_registry,
    )
