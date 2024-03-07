import dataclasses
import json
from functools import wraps
from typing import Any, Callable

from aiohttp import web
from aiohttp.web import middleware

from app.server.errors import APIError, new_internal_error

ResponseType = dict[str, Any]


@middleware
async def exception_middleware(request: web.Request, handler: Callable[[web.Request], web.Response]):
    try:
        response = await handler(request)
    except APIError as e:
        response = web.Response(text=json.dumps(dataclasses.asdict(e)))
    except Exception as e:
        error = new_internal_error(e)
        response = web.Response(text=json.dumps(dataclasses.asdict(error)))

    return response


def json_wrapper(func: Callable[[web.Request], dict[str, Any]]) -> Callable[[web.Request], web.Response]:
    @wraps(func)
    async def inner(request: web.Request) -> web.Response:
        response = await func(request)
        return web.json_response(response)

    return inner
