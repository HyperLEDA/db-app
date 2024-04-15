import dataclasses
from typing import Any

from aiohttp import web
from aiohttp_apispec import docs, request_schema, response_schema
from marshmallow import Schema, ValidationError, fields, post_load

from app import domain
from app.domain import model
from app.lib.exceptions import new_validation_error


class StartTaskRequestSchema(Schema):
    task_name = fields.Str(required=True, description="Name of the task to start")
    payload = fields.Dict(keys=fields.Str(), description="Payload to the task")

    @post_load
    def make(self, data, **kwargs) -> model.StartTaskRequest:
        return model.StartTaskRequest(**data)


class StartTaskResponseSchema(Schema):
    id = fields.Int(description="ID of the task")


@docs(
    summary="Start processing task",
    tags=["tasks"],
    description="Starts background task.",
)
@request_schema(
    StartTaskRequestSchema(),
    example=dataclasses.asdict(model.StartTaskRequest("echo", {"sleep_time_seconds": 2})),
)
@response_schema(StartTaskResponseSchema(), 200)
async def start_task_handler(actions: domain.Actions, r: web.Request) -> Any:
    request_dict = await r.json()
    try:
        request = StartTaskRequestSchema().load(request_dict)
    except ValidationError as e:
        raise new_validation_error(str(e)) from e

    return actions.start_task(request)
