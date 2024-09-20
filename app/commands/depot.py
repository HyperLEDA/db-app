from dataclasses import dataclass

from app.data import interface, repositories
from app.lib import auth, clients


@dataclass
class Depot:
    common_repo: repositories.CommonRepository
    layer0_repo: repositories.Layer0Repository
    layer2_repo: repositories.Layer2Repository
    tmp_data_repo: repositories.TmpDataRepositoryImpl
    queue_repo: interface.QueueRepository  # TODO: remove interfaces, they are not needed for DI
    authenticator: auth.Authenticator
    clients: clients.Clients
