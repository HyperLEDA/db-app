import abc
from dataclasses import dataclass

from marshmallow import Schema, fields, post_load

from app.lib.storage import postgres


@dataclass
class Config:
    storage: postgres.PgStorageConfig


class ConfigSchema(Schema):
    storage = fields.Nested(postgres.PgStorageConfigSchema(), required=True)

    @post_load
    def make(self, data, **kwargs):
        return Config(**data)


class Task(abc.ABC):
    """
    Represents an asynchronous task that performs some operation on data in the database.
    """

    @classmethod
    @abc.abstractmethod
    def name(cls):
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
