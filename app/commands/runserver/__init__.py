import logging

from app import server
from app.commands.runserver.config import parse_config


def start(config_path: str):
    cfg = parse_config(config_path)
    logging.basicConfig(level=logging.DEBUG)

    server.start(cfg.server)
