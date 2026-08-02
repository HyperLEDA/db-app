import abc
import datetime

from app.lib import config
from app.lib.storage import postgres


class Config(config.ConfigSettings):
    storage: postgres.PgStorageConfig = postgres.PgStorageConfig()


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
