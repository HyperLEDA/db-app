from typing import Any

from aiohttp import web
from marshmallow import Schema, ValidationError, fields, post_load

from app import domain
from app.domain import model
from app.lib.exceptions import new_validation_error
from app.presentation.server.handlers import common


class StartTaskRequestSchema(Schema):
    task_name = fields.Str(required=True, description="Name of the task to start", example="echo")
    payload = fields.Dict(
        keys=fields.Str(),
        description="Payload to the task",
        example={"sleep_time_seconds": 2},
    )

    @post_load
    def make(self, data, **kwargs) -> model.StartTaskRequest:
        return model.StartTaskRequest(**data)


class StartTaskResponseSchema(Schema):
    id = fields.Int(description="ID of the task")


async def start_task_handler(actions: domain.Actions, r: web.Request) -> Any:
    """---
    summary: Start processing task
    description: Starts background task.
    tags: [admin, tasks]
    requestBody:
        content:
            application/json:
                schema: StartTaskRequestSchema
    responses:
        200:
            description: Task successfully started
            content:
                application/json:
                    schema: CreateSourceResponseSchema
    """
    request_dict = await r.json()
    try:
        request = StartTaskRequestSchema().load(request_dict)
    except ValidationError as e:
        raise new_validation_error(str(e)) from e

    return actions.start_task(request)


description = common.HandlerDescription(
    common.HTTPMethod.POST,
    "/api/v1/admin/task",
    start_task_handler,
    StartTaskRequestSchema,
    StartTaskResponseSchema,
)
