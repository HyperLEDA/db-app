import datetime
import http
from typing import Annotated

import fastapi
import structlog

from app.lib.web import server
from app.presentation.dataapi import interface

logger = structlog.stdlib.get_logger()


def _query_request_dep(
    q: Annotated[str, fastapi.Query(description="Query string")],
    page_size: Annotated[int, fastapi.Query(description="Number of objects per page")] = 10,
    page: Annotated[int, fastapi.Query(description="Page number")] = 0,
) -> interface.QueryRequest:
    return interface.QueryRequest(q=q, page_size=page_size, page=page)


class API:
    def __init__(self, actions: interface.Actions) -> None:
        self.actions = actions

    def query_simple(
        self, request: Annotated[interface.QuerySimpleRequest, fastapi.Query()]
    ) -> server.APIOkResponse[interface.QuerySimpleResponse]:
        response = self.actions.query_simple(request)

        return server.APIOkResponse(data=response)

    def query(
        self,
        request: Annotated[interface.QueryRequest, fastapi.Depends(_query_request_dep)],
    ) -> server.APIOkResponse[interface.QueryResponse]:
        response = self.actions.query(request)

        return server.APIOkResponse(data=response)

    def query_fits(
        self,
        request: Annotated[interface.FITSRequest, fastapi.Query()],
    ) -> fastapi.Response:
        response = self.actions.query_fits(request)

        filename = datetime.datetime.now(datetime.UTC).strftime("%Y-%m-%d_%H-%M-%S")
        return fastapi.Response(
            content=response,
            status_code=200,
            headers={
                "Content-Disposition": f'attachment; filename="{filename}.fits"',
                "Content-Type": "application/fits",
            },
        )


class Server(server.WebServer):
    def __init__(
        self, actions: interface.Actions, config: server.ServerConfig, logger: structlog.stdlib.BoundLogger
    ) -> None:
        api = API(actions)

        routes: list[server.Route] = [
            server.Route(
                "/v1/query/simple",
                http.HTTPMethod.GET,
                api.query_simple,
                "Query data about objects",
                """Obtains data about the objects according to the specified parameters.
All of the conditions are combined with the logical AND operator.
For example, if both coordinates and designation are specified, object must be in the specified area and have
the specified designation.

Several notes:
- You cannot specify both PGC numbers and additional queries. If both are specified, only PGC numbers
will be used to query.
- The answer is paginated to improve performance.""",
            ),
            server.Route(
                "/v1/query",
                http.HTTPMethod.GET,
                api.query,
                "Query data about objects using query string",
                """Obtains objects using a free-form query string.

The string is interpreted as:
- A designation (name) search if it does not match a coordinate format; objects with matching designation are returned.
- Coordinates in HMS/DMS form (e.g. 12h30m49.32s+12d22m33.2s) or J form (e.g. J123049.32+122233.2);
  objects within 1 arcsecond are returned.
If the string matches multiple interpretations, results are combined with OR.""",
            ),
            server.Route(
                "/v1/query/fits",
                http.HTTPMethod.GET,
                api.query_fits,
                "Query data about objects and return as FITS file",
                """Obtains data about the objects according to the specified parameters and returns it as a FITS file.
All of the conditions are combined with the logical AND operator.
For example, if both coordinates and designation are specified, object must be in the specified area and have
the specified designation.""",
            ),
        ]

        super().__init__(routes, config, logger)
