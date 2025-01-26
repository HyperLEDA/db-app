from aiohttp import web
from marshmallow import Schema, ValidationError, fields, post_load

from app import schema
from app.commands.adminapi import depot
from app.domain import actions
from app.lib.web import responses, server
from app.lib.web.errors import RuleValidationError
from app.presentation.adminapi import common


class GetTaskInfoRequestSchema(Schema):
    task_id = fields.Int(required=True, description="ID of the task")

    @post_load
    def make(self, data, **kwargs) -> schema.GetTaskInfoRequest:
        return schema.GetTaskInfoRequest(**data)


class GetTaskInfoResponseSchema(Schema):
    id = fields.Int(description="ID of the task")
    task_name = fields.Str(description="Name of the task from task registry")
    status = fields.Str(description="Task status")
    payload = fields.Dict(keys=fields.Str(), description="Payload to the task")
    start_time = fields.DateTime(format="iso", description="Time when task started")
    end_time = fields.DateTime(format="iso", description="Time when task ended")
    message = fields.Dict(keys=fields.Str(), description="Message associated with the task status")


async def get_task_info_handler(dpt: depot.Depot, r: web.Request) -> responses.APIOkResponse:
    """---
    summary: Get information about the task
    description: Retrieves information about the task using its id.
    security:
        - TokenAuth: []
    tags: [tasks, admin]
    parameters:
      - in: query
        schema: GetTaskInfoRequestSchema
    responses:
        200:
            description: Task was successfully obtained
            content:
                application/json:
                    schema:
                        type: object
                        properties:
                            data: GetTaskInfoResponseSchema
    """
    try:
        request = GetTaskInfoRequestSchema().load(r.rel_url.query)
    except ValidationError as e:
        raise RuleValidationError(str(e)) from e

    return responses.APIOkResponse(actions.get_task_info(dpt, request))


description = common.handler_description(
    server.HTTPMethod.GET,
    "/api/v1/admin/task",
    get_task_info_handler,
    GetTaskInfoRequestSchema,
    GetTaskInfoResponseSchema,
)
