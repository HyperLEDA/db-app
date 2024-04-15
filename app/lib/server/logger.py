import structlog
from aiohttp import abc, web

log: structlog.stdlib.BoundLogger = structlog.get_logger()


class AccessLogger(abc.AbstractAccessLogger):
    def log(self, request: web.BaseRequest, response: web.StreamResponse, time: float) -> None:
        log.info(
            "request",
            method=request.method,
            remote=request.remote,
            path=request.path,
            elapsed=f"{time:.03f}s",
            query=dict(request.query),
            response_status=response.status,
            request_content_type=request.content_type,
            response_content_type=response.content_type,
        )
