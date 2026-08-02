import contextlib
import json
from collections.abc import Awaitable, Callable, Mapping

import fastapi
from opentelemetry import trace
from opentelemetry.sdk.trace.id_generator import RandomIdGenerator
from starlette import types
from starlette.middleware import base as middlewares

from app.lib.audit import truncate
from app.lib.web.middlewares.auth import identity_from_request

_tracer = trace.get_tracer("adminapi.run")
_id_generator = RandomIdGenerator()


@contextlib.contextmanager
def run_span(run_id: str | None, method: str):
    if run_id is None:
        yield
        return
    span_ctx = trace.SpanContext(
        trace_id=int(run_id[:32], 16),
        span_id=_id_generator.generate_span_id(),
        is_remote=True,
        trace_flags=trace.TraceFlags(trace.TraceFlags.SAMPLED),
    )
    parent = trace.set_span_in_context(trace.NonRecordingSpan(span_ctx))
    with _tracer.start_as_current_span(method, context=parent):
        yield


def _parsed_body(body: bytes) -> dict[str, object] | None:
    if not body:
        return None
    try:
        parsed = json.loads(body)
    except json.JSONDecodeError:
        return None
    return parsed if isinstance(parsed, dict) else None


def _action_description_from_body(parsed: dict[str, object] | None) -> str | None:
    if parsed is None:
        return None
    raw = parsed.get("action_description")
    return raw if isinstance(raw, str) else None


def _truncated_request_from_body(parsed: dict[str, object] | None) -> dict[str, object] | None:
    if parsed is None:
        return None
    return truncate.truncate_request(parsed)


class ActionMiddleware(middlewares.BaseHTTPMiddleware):
    def __init__(
        self,
        app: types.ASGIApp,
        tracked_actions: Mapping[tuple[str, str], str],
        record_action: Callable[[int, str, str | None, dict[str, object] | None], None],
        run_id: Callable[[int, str, str], str],
    ) -> None:
        self._tracked_actions = tracked_actions
        self._record_action = record_action
        self._run_id = run_id
        super().__init__(app)

    async def dispatch(
        self,
        request: fastapi.Request,
        call_next: Callable[[fastapi.Request], Awaitable[fastapi.Response]],
    ) -> fastapi.Response:
        method_name = self._tracked_actions.get((request.url.path, request.method.lower()))
        if method_name is None:
            return await call_next(request)

        auth_ctx = identity_from_request(request)
        user_id = auth_ctx.user.user_id if auth_ctx is not None else None

        parsed_body = _parsed_body(await request.body())
        action_description = _action_description_from_body(parsed_body)
        truncated_request = _truncated_request_from_body(parsed_body)
        resolved_run_id = (
            self._run_id(user_id, method_name, action_description)
            if user_id is not None and action_description
            else None
        )

        with run_span(resolved_run_id, method_name):
            response = await call_next(request)

        if user_id is not None:
            self._record_action(user_id, method_name, action_description, truncated_request)

        return response
