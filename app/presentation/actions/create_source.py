import dataclasses
import logging

from app.presentation.model import CreateSourceRequest, CreateSourceResponse


def create_source(r: CreateSourceRequest) -> CreateSourceResponse:
    logging.info(dataclasses.asdict(r))

    return CreateSourceResponse(id=42)
