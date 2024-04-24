from typing import Any

from aiohttp import web
from marshmallow import Schema, ValidationError, fields, post_load

from app import domain
from app.domain import model
from app.lib.exceptions import new_validation_error
from app.presentation.server.handlers import common


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
    message = fields.Dict(keys=fields.Str(), description="Message associated with the task status")


async def get_task_info_handler(actions: domain.Actions, r: web.Request) -> Any:
    """---
    summary: Get information about the task
    description: Retrieves information about the task using its id.
    tags: [tasks, admin]
    parameters:
      - in: query
        schema: GetTaskInfoRequestSchema
    responses:
        200:
            description: Task was successfully obtained
            content:
                application/json:
                    schema: GetTaskInfoResponseSchema
    """
    try:
        request = GetTaskInfoRequestSchema().load(r.rel_url.query)
    except ValidationError as e:
        raise new_validation_error(str(e)) from e

    return actions.get_task_info(request)


description = common.HandlerDescription(get_task_info_handler, GetTaskInfoRequestSchema, GetTaskInfoResponseSchema)
