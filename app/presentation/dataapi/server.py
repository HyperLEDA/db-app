import http
from typing import Annotated

import fastapi
import structlog

from app.lib.web import server
from app.presentation.dataapi import interface

logger = structlog.stdlib.get_logger()


class API:
    def __init__(self, actions: interface.Actions) -> None:
        self.actions = actions

    def query_simple(
        self, request: Annotated[interface.QuerySimpleRequest, fastapi.Query()]
    ) -> server.APIOkResponse[interface.QuerySimpleResponse]:
        response = self.actions.query_simple(request)

        return server.APIOkResponse(data=response)


class Server2(server.FastAPIServer):
    def __init__(
        self, actions: interface.Actions, config: server.ServerConfig, logger: structlog.stdlib.BoundLogger
    ) -> None:
        api = API(actions)

        routes: list[server.FastAPIRoute] = [
            server.FastAPIRoute(
                "/api/v1/query/simple",
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
            )
        ]

        super().__init__(routes, config, logger)


class Server(server.WebServer):
    def __init__(self, actions: interface.Actions, config: server.ServerConfig, *args, **kwargs):
        self.actions = actions

        routes: list[server.Route] = [
            # server.ActionRoute(
            #     actions,
            #     server.RouteInfo(
            #         http.HTTPMethod.GET,
            #         "/api/v1/query/simple",
            #         query_simple.QuerySimpleRequestSchema,
            #         query_simple.QuerySimpleResponseSchema,
            #     ),
            #     query_simple.query_simple_handler,
            # ),
            # server.ActionRoute(
            #     actions,
            #     server.RouteInfo(
            #         http.HTTPMethod.GET,
            #         "/api/v1/query",
            #         query.QueryRequestSchema,
            #         query.QueryResponseSchema,
            #     ),
            #     query.query_handler,
            # ),
            # server.ActionRoute(
            #     actions,
            #     server.RouteInfo(
            #         http.HTTPMethod.GET,
            #         "/api/v1/query/fits",
            #         fits.FITSRequestSchema,
            #         None,
            #     ),
            #     fits.fits_handler,
            # ),
        ]

        super().__init__(routes, config, *args, **kwargs)
