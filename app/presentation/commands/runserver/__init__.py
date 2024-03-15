import logging

from app.data import Storage
from app.data.repository import DataRespository
from app.domain import usecases
from app.presentation import server
from app.presentation.commands.runserver.config import parse_config


def start(config_path: str):
    cfg = parse_config(config_path)
    logging.basicConfig(level=logging.DEBUG)

    storage = Storage(cfg.storage)
    storage.connect()

    repo = DataRespository(storage)
    actions = usecases.Actions(repo)

    server.start(cfg.server, actions)
    storage.disconnect()
