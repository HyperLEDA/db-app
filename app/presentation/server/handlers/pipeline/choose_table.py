import dataclasses
from typing import Any

from aiohttp import web
from aiohttp_apispec import docs, request_schema, response_schema
from marshmallow import ValidationError

from app import domain
from app.domain.model import ChooseTableRequest
from app.lib.exceptions import new_validation_error
from app.presentation.model import ChooseTableRequestSchema, ChooseTableResponseSchema


@docs(
    summary="Choose table to process",
    tags=["pipeline"],
    description="Select table for download and returns ID of the processing pipeline.",
)
@request_schema(
    ChooseTableRequestSchema(),
    example=dataclasses.asdict(ChooseTableRequest("J/AJ/135/2177", "J/AJ/135/2177/table1")),
)
@response_schema(ChooseTableResponseSchema(), 200)
async def choose_table(actions: domain.Actions, r: web.Request) -> Any:
    request_dict = await r.json()
    try:
        request = ChooseTableRequestSchema().load(request_dict)
    except ValidationError as e:
        raise new_validation_error(str(e)) from e

    return actions.choose_table(request)
