from dataclasses import dataclass

from app.data import interface
from app.lib import auth, clients


@dataclass
class Depot:
    common_repo: interface.CommonRepository
    layer0_repo: interface.Layer0Repository
    queue_repo: interface.QueueRepository
    authenticator: auth.Authenticator
    clients: clients.Clients
