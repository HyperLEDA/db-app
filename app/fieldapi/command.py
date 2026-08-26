from pathlib import Path
from typing import final

import pydantic
import structlog
import yaml

from app.fieldapi import config as fieldapi_config
from app.fieldapi import domain, presentation
from app.fieldapi.providers import registry
from app.lib import auth, commands, config, tracing
from app.lib.tracing import TracingConfig
from app.lib.web import server

log: structlog.stdlib.BoundLogger = structlog.get_logger()


class Config(config.ConfigSettings):
    server: server.ServerConfig
    datasets: fieldapi_config.DatasetsConfig
    tracing: TracingConfig = pydantic.Field(
        default_factory=lambda: TracingConfig(endpoint="localhost:4317", enabled=False)
    )


def parse_config(path: str) -> Config:
    data = yaml.safe_load(Path(path).read_text())
    return Config(**data)


@final
class FieldAPICommand(commands.Command):
    def __init__(self, config_path: str) -> None:
        self.config_path = config_path
        self.dataset_registry: registry.DatasetRegistry | None = None
        self.app: presentation.Server | None = None

    def prepare(self) -> None:
        self.config = parse_config(self.config_path)

        tracing.setup_tracing("fieldapi", self.config.tracing)

        self.dataset_registry = registry.DatasetRegistry.from_config(
            self.config.datasets.data_dir,
            self.config.datasets.enabled,
        )

        actions = domain.Actions(self.dataset_registry)
        self.app = presentation.Server(
            actions,
            self.config.server,
            log,
            auth.NoopAuthenticator(),
            auth_enabled=False,
        )

    def run(self) -> None:
        if self.app is None:
            raise RuntimeError("server was not prepared")
        self.app.run()

    def cleanup(self) -> None:
        self.dataset_registry = None
        self.app = None
