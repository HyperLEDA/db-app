import dataclasses
import logging

from aiohttp import web
from aiohttp_apispec import docs, request_schema, response_schema
from marshmallow import ValidationError

from app import server
from app.server.errors.apierror import APIError, new_validation_error
from app.server.schema import CreateSourceRequestSchema, CreateSourceResponse, CreateSourceResponseSchema


@docs(
    summary="Create new source",
    tags=["sources"],
    description="Creates new source that can be referenced when adding new objects.",
)
@request_schema(CreateSourceRequestSchema())
@response_schema(CreateSourceResponseSchema(), 200)
@response_schema(APIError(), 400)
async def create_source(r: web.Request) -> server.ResponseType:
    request_dict = await r.json()
    try:
        request = CreateSourceRequestSchema().load(request_dict)
    except ValidationError as e:
        raise new_validation_error(str(e))

    logging.info(dataclasses.asdict(request))

    response = CreateSourceResponse(id=42)

    return {"data": dataclasses.asdict(response)}
