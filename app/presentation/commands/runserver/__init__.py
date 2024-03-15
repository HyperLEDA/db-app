import logging

from app.data import Storage
from app.presentation import server
from app.presentation.commands.runserver.config import parse_config


def start(config_path: str):
    cfg = parse_config(config_path)
    logging.basicConfig(level=logging.DEBUG)

    storage = Storage(cfg.storage)
    storage.connect()

    server.start(cfg.server)
    storage.disconnect()
