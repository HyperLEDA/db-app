import datetime
from unittest import mock

from app.domain.adminapi import actions
from app.lib import auth, clients
from app.presentation import adminapi


def get_mock_table_stats_cache() -> mock.MagicMock:
    cache_mock = mock.MagicMock()
    cache_mock.get.return_value = adminapi.TableStatsSnapshot(
        tables={},
        computed_at=datetime.datetime.now(tz=datetime.UTC),
    )
    return cache_mock


def get_mock_actions():
    c = clients.Clients(ads_token="test")
    c.ads = mock.MagicMock()
    c.vizier = mock.MagicMock()

    return actions.Actions(
        common_repo=mock.MagicMock(),
        layer0_repo=mock.MagicMock(),
        layer1_repo=mock.MagicMock(),
        layer2_repo=mock.MagicMock(),
        designation_rules_repo=mock.MagicMock(),
        authenticator=auth.NoopAuthenticator(),
        clients=c,
        table_stats_cache=get_mock_table_stats_cache(),
    )
