import dataclasses
import logging

from app.server.schema import GetSourceRequest, GetSourceResponse


def get_source(r: GetSourceRequest) -> GetSourceResponse:
    logging.info(dataclasses.asdict(r))

    return GetSourceResponse(type="table", metadata={"name": "haha funny name"})
