import http

from app.lib.web import server
from app.presentation.dataapi import fits, interface, query, query_simple


class Server(server.WebServer):
    def __init__(self, actions: interface.Actions, config: server.ServerConfig, *args, **kwargs):
        self.actions = actions

        routes: list[server.Route] = [
            server.ActionRoute(
                actions,
                server.RouteInfo(
                    http.HTTPMethod.GET,
                    "/api/v1/query/simple",
                    query_simple.QuerySimpleRequestSchema,
                    query_simple.QuerySimpleResponseSchema,
                ),
                query_simple.query_simple_handler,
            ),
            server.ActionRoute(
                actions,
                server.RouteInfo(
                    http.HTTPMethod.GET,
                    "/api/v1/query",
                    query.QueryRequestSchema,
                    query.QueryResponseSchema,
                ),
                query.query_handler,
            ),
            server.ActionRoute(
                actions,
                server.RouteInfo(
                    http.HTTPMethod.GET,
                    "/api/v1/query/fits",
                    fits.FITSRequestSchema,
                    None,
                ),
                fits.fits_handler,
            ),
        ]

        super().__init__(routes, config, *args, **kwargs)
