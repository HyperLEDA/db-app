import gzip

from starlette import types


class GzipRequestMiddleware:
    def __init__(self, app: types.ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: types.Scope, receive: types.Receive, send: types.Send) -> None:
        if scope["type"] != "http" or dict(scope["headers"]).get(b"content-encoding") != b"gzip":
            await self.app(scope, receive, send)
            return

        compressed = b""
        while True:
            message = await receive()
            compressed += message.get("body", b"")
            if not message.get("more_body", False):
                break

        body = gzip.decompress(compressed)
        scope["headers"] = [
            (key, value) for key, value in scope["headers"] if key not in (b"content-encoding", b"content-length")
        ] + [(b"content-length", str(len(body)).encode())]

        delivered = False

        async def receive_decompressed() -> types.Message:
            nonlocal delivered
            if delivered:
                return {"type": "http.disconnect"}
            delivered = True
            return {"type": "http.request", "body": body, "more_body": False}

        await self.app(scope, receive_decompressed, send)
