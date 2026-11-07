import abc
import datetime

import pydantic

from app.lib import config, velocity_config
from app.lib.storage import postgres
from app.specs.fieldapi import FieldAPIConfig


class Config(config.ConfigSettings):
    storage: postgres.PgStorageConfig = postgres.PgStorageConfig()
    fieldapi: FieldAPIConfig = pydantic.Field(default_factory=FieldAPIConfig)
    catalogs: velocity_config.CatalogConfig = pydantic.Field(default_factory=velocity_config.CatalogConfig)


def parse_since(since: datetime.datetime | str | None) -> datetime.datetime | None:
    if since is None:
        return None
    if isinstance(since, datetime.datetime):
        dt = since
    else:
        dt = datetime.datetime.fromisoformat(str(since).replace("Z", "+00:00"))
    if dt.tzinfo is None:
        return dt.replace(tzinfo=datetime.UTC)
    return dt


class Task(abc.ABC):
    """
    Represents a task that performs some operation on data in the database.
    """

    @classmethod
    @abc.abstractmethod
    def name(cls) -> str:
        pass

    @abc.abstractmethod
    def prepare(self, config: Config):
        pass

    @abc.abstractmethod
    def run(self):
        pass

    @abc.abstractmethod
    def cleanup(self):
        pass
