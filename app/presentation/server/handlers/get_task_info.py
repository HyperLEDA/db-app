from typing import Any

from aiohttp import web
from aiohttp_apispec import docs, querystring_schema, response_schema
from marshmallow import ValidationError

from app import domain
from app.lib.exceptions import new_validation_error
from app.presentation.model import GetTaskInfoRequestSchema, GetTaskInfoResponseSchema


@docs(
    summary="Get information about the task",
    tags=["tasks"],
    description="Retrieves information about the task using its id.",
)
@querystring_schema(GetTaskInfoRequestSchema())
@response_schema(GetTaskInfoResponseSchema(), 200)
async def get_task_info(actions: domain.Actions, r: web.Request) -> Any:
    try:
        request = GetTaskInfoRequestSchema().load(r.rel_url.query)
    except ValidationError as e:
        raise new_validation_error(str(e)) from e

    return actions.get_task_info(request)
