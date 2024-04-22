from typing import Any

from aiohttp import web
from aiohttp_apispec import docs, querystring_schema, response_schema
from marshmallow import Schema, ValidationError, fields, post_load

from app import domain
from app.domain import model
from app.lib.exceptions import new_validation_error


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


@docs(
    summary="Get information about the task",
    tags=["tasks", "admin"],
    description="Retrieves information about the task using its id.",
)
@querystring_schema(GetTaskInfoRequestSchema())
@response_schema(GetTaskInfoResponseSchema(), 200)
async def get_task_info_handler(actions: domain.Actions, r: web.Request) -> Any:
    try:
        request = GetTaskInfoRequestSchema().load(r.rel_url.query)
    except ValidationError as e:
        raise new_validation_error(str(e)) from e

    return actions.get_task_info(request)
