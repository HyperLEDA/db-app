import enum
from dataclasses import dataclass
from typing import Callable


class HTTPMethod(enum.Enum):
    GET = "GET"
    POST = "POST"
    # add more if needed


@dataclass
class HandlerDescription:
    method: HTTPMethod
    endpoint: str
    handler: Callable
    request_schema: type
    response_schema: type
