from app.lib.web import server
from app.presentation.dataapi import interface, query_simple


class Server(server.WebServer):
    def __init__(self, actions: interface.Actions, config: server.ServerConfig, *args, **kwargs):
        self.actions = actions

        routes: list[server.Route] = [
            server.ActionRoute(
                actions,
                server.RouteInfo(
                    server.HTTPMethod.GET,
                    "/api/v1/query/simple",
                    query_simple.QuerySimpleRequestSchema,
                    query_simple.QuerySimpleResponseSchema,
                ),
                query_simple.query_simple_handler,
            ),
        ]

        super().__init__(routes, config, *args, **kwargs)
