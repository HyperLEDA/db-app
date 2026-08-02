import http
from typing import Annotated

import fastapi
import structlog

from app.dataapi.presentation import interface, tap
from app.lib import auth
from app.lib.web import server

logger = structlog.stdlib.get_logger()


class API:
    def __init__(self, actions: interface.Actions) -> None:
        self.actions = actions

    def query_simple(
        self, request: Annotated[interface.QuerySimpleRequest, fastapi.Query()]
    ) -> server.APIOkResponse[interface.QuerySimpleResponse]:
        response = self.actions.query_simple(request)

        return server.APIOkResponse(data=response)

    def tap_tables(
        self,
        request: Annotated[tap.ListTAPTablesRequest, fastapi.Query()],
    ) -> server.APIOkResponse[tap.ListTAPTablesResponse]:
        response = self.actions.tap_tables(request)
        return server.APIOkResponse(data=response)

    def tap_sync(
        self,
        request: fastapi.Request,
        tap_request: Annotated[tap.TAPSyncRequest, fastapi.Query()],
    ) -> server.APIOkResponse[tap.TAPSyncResponse]:
        _ = request
        response = self.actions.tap_sync(tap_request)
        return server.APIOkResponse(data=response)


class Server(server.WebServer):
    def __init__(
        self,
        actions: interface.Actions,
        config: server.ServerConfig,
        logger: structlog.stdlib.BoundLogger,
        authenticator: auth.Authenticator,
        auth_enabled: bool = True,
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
- Use the catalogs query parameter to limit which catalogs are returned (e.g. catalogs=icrs&catalogs=designation).
- The answer is paginated to improve performance.""",
            ),
            server.Route(
                "/v1/tap/tables",
                http.HTTPMethod.GET,
                api.tap_tables,
                "List TAP table metadata for whitelisted schemas.",
            ),
            server.Route(
                "/v1/tap/sync",
                http.HTTPMethod.GET,
                api.tap_sync,
                "Execute an arbitrary SQL query (TAP /sync).",
                "Runs a read-only SQL query against whitelisted schemas and returns a VOTable-like JSON payload.",
                rate_limit="60/minute",
            ),
        ]

        super().__init__(routes, config, logger, authenticator, auth_enabled=auth_enabled)
