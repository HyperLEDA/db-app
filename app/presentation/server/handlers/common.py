from dataclasses import dataclass
from typing import Callable


@dataclass
class HandlerDescription:
    handler: Callable
    request_schema: type
    response_schema: type
