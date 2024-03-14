import logging

from data import Storage
from presentation import server
from presentation.commands.runserver.config import parse_config


def start(config_path: str):
    cfg = parse_config(config_path)
    logging.basicConfig(level=logging.DEBUG)

    storage = Storage(cfg.storage)
    storage.connect()

    storage.exec(
        "INSERT INTO common.bib (bibcode, year, author, title) VALUES (%s, %s, %s, %s)", 
        ['wewerwr', 2022, ['me'], 'cool title'])

    server.start(cfg.server)
    storage.disconnect()
