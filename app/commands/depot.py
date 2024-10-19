from dataclasses import dataclass
from unittest import mock

from app.data import repositories
from app.lib import auth, clients


@dataclass
class Depot:
    common_repo: repositories.CommonRepository
    layer0_repo: repositories.Layer0Repository
    layer1_repo: repositories.Layer1Repository
    layer2_repo: repositories.Layer2Repository
    tmp_data_repo: repositories.TmpDataRepositoryImpl
    queue_repo: repositories.QueueRepository
    authenticator: auth.Authenticator
    clients: clients.Clients


def get_mock_depot() -> Depot:
    c = clients.Clients(ads_token="test")
    c.ads = mock.MagicMock()
    c.vizier = mock.MagicMock()

    return Depot(
        common_repo=mock.MagicMock(),
        layer0_repo=mock.MagicMock(),
        layer1_repo=mock.MagicMock(),
        layer2_repo=mock.MagicMock(),
        tmp_data_repo=mock.MagicMock(),
        queue_repo=mock.MagicMock(),
        authenticator=auth.NoopAuthenticator(),
        clients=c,
    )
