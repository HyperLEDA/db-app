from typing import Awaitable, Callable

import structlog
from aiohttp import web

from app.lib import exceptions

log: structlog.stdlib.BoundLogger = structlog.get_logger()


@web.middleware
async def exception_middleware(
    request: web.Request, handler: Callable[[web.Request], Awaitable[web.StreamResponse]]
) -> web.StreamResponse:
    try:
        response = await handler(request)
    except exceptions.APIException as e:
        log.exception(str(e))
        response = web.json_response(e.dict(), status=e.status)
    except Exception as e:
        exc = exceptions.new_internal_error(e)
        log.exception(str(exc))
        response = web.json_response(exc.dict(), status=500)

    return response
