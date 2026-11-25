import abc
import datetime

import pydantic
import pydantic_settings as settings

from app.lib import config
from app.lib.storage import postgres
from app.lib.tracing import TracingConfig
from app.specs.fieldapi import FieldAPIConfig


class WorkerConfig(config.ConfigSettings):
    model_config = settings.SettingsConfigDict(env_prefix="TASKS_")

    work_pool_name: str
    image: str
    work_pool_concurrency: int
    docker_network: str
    docker_container_prefix: str

    @classmethod
    def from_env(cls) -> "WorkerConfig":
        return cls()  # pyright: ignore[reportCallIssue] - values come from TASKS_* env vars


class Config(config.ConfigSettings):
    storage: postgres.PgStorageConfig = postgres.PgStorageConfig()
    fieldapi: FieldAPIConfig = pydantic.Field(default_factory=FieldAPIConfig)
    tracing: TracingConfig = pydantic.Field(default_factory=TracingConfig)


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
