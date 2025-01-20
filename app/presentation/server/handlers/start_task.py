from aiohttp import web
from marshmallow import Schema, ValidationError, fields, post_load

from app import commands, schema
from app.domain import actions
from app.lib.web import responses, server
from app.lib.web.errors import RuleValidationError
from app.presentation.server.handlers import common


class StartTaskRequestSchema(Schema):
    task_name = fields.Str(required=True, description="Name of the task to start", example="echo")
    payload = fields.Dict(
        keys=fields.Str(),
        description="Payload to the task",
        example={"sleep_time_seconds": 2},
    )

    @post_load
    def make(self, data, **kwargs) -> schema.StartTaskRequest:
        return schema.StartTaskRequest(**data)


class StartTaskResponseSchema(Schema):
    id = fields.Int(description="ID of the task")


async def start_task_handler(depot: commands.Depot, r: web.Request) -> responses.APIOkResponse:
    """---
    summary: Start processing task
    description: Starts background task.
    security:
        - TokenAuth: []
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
                    schema:
                        type: object
                        properties:
                            data: CreateSourceResponseSchema
    """
    request_dict = await r.json()
    try:
        request = StartTaskRequestSchema().load(request_dict)
    except ValidationError as e:
        raise RuleValidationError(str(e)) from e

    return responses.APIOkResponse(actions.start_task(depot, request))


description = common.handler_description(
    server.HTTPMethod.POST,
    "/api/v1/admin/task",
    start_task_handler,
    StartTaskRequestSchema,
    StartTaskResponseSchema,
)
