from dataclasses import dataclass
import dataclasses
import json
from typing import Any, Callable
from aiohttp import web
from aiohttp.web import middleware


ResponseType = dict[str, Any]


@middleware
async def exception_middleware(request: web.Request, handler: Callable[[web.Request], web.Response]):
    try:
        response = await handler(request)
    except Exception as e:
        error = APIError("internal_error", str(e))
        response = web.Response(text=json.dumps(dataclasses.asdict(error)))

    return response


@dataclass
class APIError:
    code: str
    message: str


def json_wrapper(func: Callable[[web.Request], dict[str, Any]]) -> Callable[[web.Request], web.Response]:
    async def inner(request: web.Request) -> web.Response:
        response = await func(request)
        return web.Response(text=json.dumps(response))

    return inner
