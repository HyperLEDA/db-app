from dataclasses import dataclass

from marshmallow import Schema, fields, post_load

from app.lib import config


@dataclass
class QueueConfig:
    endpoint: str
    port: int
    queue_name: str


class QueueConfigSchema(Schema):
    endpoint = fields.Str(required=True)
    port = config.EnvField("QUEUE_PORT", fields.Int(required=True))
    queue_name = fields.Str(required=True)

    @post_load
    def make(self, data, **kwargs):
        return QueueConfig(**data)
