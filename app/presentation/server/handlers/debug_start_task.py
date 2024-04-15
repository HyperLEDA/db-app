import dataclasses
from typing import Any

from aiohttp import web
from aiohttp_apispec import docs, request_schema, response_schema
from marshmallow import ValidationError

from app import domain
from app.domain.model.task import StartTaskRequest
from app.lib.exceptions import new_validation_error
from app.presentation.server.handlers import start_task


@docs(
    summary="Start processing task in debug mode",
    tags=["tasks"],
    description="Starts task synchronously.",
)
@request_schema(
    start_task.StartTaskRequestSchema(),
    example=dataclasses.asdict(StartTaskRequest("echo", {"sleep_time_seconds": 2})),
)
@response_schema(start_task.StartTaskResponseSchema(), 200)
async def debug_start_task_handler(actions: domain.Actions, r: web.Request) -> Any:
    request_dict = await r.json()
    try:
        request = start_task.StartTaskRequestSchema().load(request_dict)
    except ValidationError as e:
        raise new_validation_error(str(e)) from e

    return actions.debug_start_task(request)
