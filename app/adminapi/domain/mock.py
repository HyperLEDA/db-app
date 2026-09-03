import datetime

from app.adminapi import clients
from app.adminapi.domain import actions
from app.lib import auth, mock
from app.specs import adminapi as spec


def get_mock_table_stats_cache() -> mock.MagicMock:
    cache_mock = mock.MagicMock()
    cache_mock.get.return_value = spec.TableStatsSnapshot(
        tables={},
        computed_at=datetime.datetime.now(tz=datetime.UTC),
    )
    return cache_mock


def get_mock_actions():
    return actions.Actions(
        repo=mock.MagicMock(),
        authenticator=auth.NoopAuthenticator(),
        storage=mock.MagicMock(),
        clients=clients.get_mock_clients(),
        table_stats_cache=get_mock_table_stats_cache(),
    )
