import abc

from app.lib import config
from app.lib.storage import postgres


class Config(config.ConfigSettings):
    storage: postgres.PgStorageConfig


class Task(abc.ABC):
    """
    Represents an asynchronous task that performs some operation on data in the database.
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
