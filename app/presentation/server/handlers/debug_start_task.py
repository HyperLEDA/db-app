from typing import Any

from aiohttp import web
from marshmallow import ValidationError

from app import domain
from app.lib.exceptions import new_validation_error
from app.presentation.server.handlers import common, start_task


async def debug_start_task_handler(actions: domain.Actions, r: web.Request) -> Any:
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
                    schema:
                        type: object
                        properties:
                            data: CreateSourceResponseSchema
    """
    request_dict = await r.json()
    try:
        request = start_task.StartTaskRequestSchema().load(request_dict)
    except ValidationError as e:
        raise new_validation_error(str(e)) from e

    return actions.debug_start_task(request)


description = common.HandlerDescription(
    common.HTTPMethod.POST,
    "/api/v1/admin/debug/task",
    debug_start_task_handler,
    start_task.StartTaskRequestSchema,
    start_task.StartTaskResponseSchema,
)
