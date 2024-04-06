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


class GetTaskInfoRequestSchema(Schema):
    task_id = fields.Int(required=True, description="ID of the task")

    @post_load
    def make(self, data, **kwargs) -> model.GetTaskInfoRequest:
        return model.GetTaskInfoRequest(**data)


class GetTaskInfoResponseSchema(Schema):
    id = fields.Int(description="ID of the task")
    task_name = fields.Str(description="Name of the task from task registry")
    status = fields.Str(description="Task status")
    payload = fields.Dict(keys=fields.Str(), description="Payload to the task")
    start_time = fields.DateTime(format="iso", description="Time when task started")
    end_time = fields.DateTime(format="iso", description="Time when task ended")
