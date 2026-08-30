import http
from typing import Annotated

import fastapi
import structlog

from app.dataapi.presentation import interface
from app.lib import auth
from app.lib.web import server
from app.specs import dataapi as spec

logger = structlog.stdlib.get_logger()


class API:
    def __init__(self, actions: interface.Actions) -> None:
        self.actions = actions

    def query_simple(
        self, request: Annotated[spec.QuerySimpleRequest, fastapi.Query()]
    ) -> server.APIOkResponse[spec.QuerySimpleResponse]:
        response = self.actions.query_simple(request)

        return server.APIOkResponse(data=response)

    def tap_tables(
        self,
        request: Annotated[spec.ListTAPTablesRequest, fastapi.Query()],
    ) -> server.APIOkResponse[spec.ListTAPTablesResponse]:
        response = self.actions.tap_tables(request)
        return server.APIOkResponse(data=response)

    def tap_sync(
        self,
        request: fastapi.Request,
        tap_request: Annotated[spec.TAPSyncRequest, fastapi.Query()],
    ) -> server.APIOkResponse[spec.TAPSyncResponse]:
        _ = request
        response = self.actions.tap_sync(tap_request)
        return server.APIOkResponse(data=response)

    def calculate_reddening(
        self, request: spec.CalculateReddeningRequest
    ) -> server.APIOkResponse[spec.CalculateReddeningResponse]:
        response = self.actions.calculate_reddening(request)
        return server.APIOkResponse(data=response)

    def list_reddening_references(self) -> server.APIOkResponse[spec.ListReddeningReferencesResponse]:
        response = self.actions.list_reddening_references()
        return server.APIOkResponse(data=response)


class Server(server.WebServer):
    def __init__(
        self,
        actions: interface.Actions,
        config: server.ServerConfig,
        logger: structlog.stdlib.BoundLogger,
    ) -> None:
        api = API(actions)

        routes: list[server.Route] = [
            server.Route(
                "/v1/query/simple",
                http.HTTPMethod.GET,
                api.query_simple,
                "Query data about objects",
                """Obtains data about the objects according to the specified parameters.
Exactly one search filter may be used at a time: pgcs, name, or a coordinate cone.

Several notes:
- Coordinate searches use equatorial (ra/dec), galactic (glon/glat), or
supergalactic (sgl/sgb) coordinates with radius.
For equatorial coordinates, eq_epoch sets the equinox (default J2000); non-J2000 coordinates
are precessed to ICRS. Galactic and supergalactic coordinates are converted to ICRS before searching.
When coordinates are specified, results are sorted by increasing distance to the search center.
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
            server.Route(
                "/v1/references/reddening",
                http.HTTPMethod.GET,
                api.list_reddening_references,
                "List photometric systems supported by the reddening calculator.",
            ),
            server.Route(
                "/v1/calculator/reddening",
                http.HTTPMethod.POST,
                api.calculate_reddening,
                "Calculate reddening for a batch of sky positions.",
                "Returns SFD E(B-V) and F99 extinction in each filter of the requested photometric system.",
            ),
        ]

        super().__init__(routes, config, logger, auth.NoopAuthenticator(), auth_enabled=False)
