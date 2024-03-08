import dataclasses
import logging

from app.server.schema import CreateSourceRequest, CreateSourceResponse


def create_source(r: CreateSourceRequest) -> CreateSourceResponse:
    logging.info(dataclasses.asdict(r))

    return CreateSourceResponse(id=42)
