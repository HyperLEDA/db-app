from aiohttp import web
from marshmallow import Schema, ValidationError, fields

from app.lib.web import responses, schema
from app.lib.web.errors import RuleValidationError
from app.presentation.adminapi import interface


class GetTaskInfoRequestSchema(schema.RequestSchema):
    task_id = fields.Int(required=True, description="ID of the task")

    class Meta:
        model = interface.GetTaskInfoRequest


class GetTaskInfoResponseSchema(Schema):
    id = fields.Int(description="ID of the task")
    task_name = fields.Str(description="Name of the task from task registry")
    status = fields.Str(description="Task status")
    payload = fields.Dict(keys=fields.Str(), description="Payload to the task")
    start_time = fields.DateTime(format="iso", description="Time when task started")
    end_time = fields.DateTime(format="iso", description="Time when task ended")
    message = fields.Dict(keys=fields.Str(), description="Message associated with the task status")


async def get_task_info_handler(actions: interface.Actions, r: web.Request) -> responses.APIOkResponse:
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

    return responses.APIOkResponse(actions.get_task_info(request))
