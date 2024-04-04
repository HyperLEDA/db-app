from marshmallow import Schema, fields, post_load

from app.domain import model


class StartTaskRequestSchema(Schema):
    task_name = fields.Str(required=True, description="Name of the task to start")
    payload = fields.Dict(keys=fields.Str(), description="Payload to the task")

    @post_load
    def make(self, data, **kwargs) -> model.StartTaskRequest:
        return model.StartTaskRequest(**data)


class StartTaskResponseSchema(Schema):
    id = fields.Int(description="ID of the task")
