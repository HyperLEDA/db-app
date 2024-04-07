from dataclasses import dataclass

from marshmallow import Schema, fields, post_load


@dataclass
class QueueConfig:
    endpoint: str
    port: int
    queue_name: str


class QueueConfigSchema(Schema):
    endpoint = fields.Str(required=True)
    port = fields.Int(required=True)
    queue_name = fields.Str(required=True)

    @post_load
    def make(self, data, **kwargs):
        return QueueConfig(**data)
