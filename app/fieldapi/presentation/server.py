import http

import structlog

from app.fieldapi.presentation import interface
from app.lib import auth
from app.lib.web import server
from app.specs import fieldapi as spec

logger = structlog.stdlib.get_logger()


class API:
    def __init__(self, actions: interface.Actions) -> None:
        self.actions = actions

    def list_datasets(self) -> server.APIOkResponse[spec.ListDatasetsResponse]:
        return server.APIOkResponse(data=self.actions.list_datasets())

    def sample(self, request: spec.SampleRequest) -> server.APIOkResponse[spec.SampleResponse]:
        return server.APIOkResponse(data=self.actions.sample(request))


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
                "/v1/datasets",
                http.HTTPMethod.GET,
                api.list_datasets,
                "List configured spatial datasets.",
            ),
            server.Route(
                "/v1/sample",
                http.HTTPMethod.POST,
                api.sample,
                "Sample a spatial dataset at the given coordinates.",
                "Returns one value per coordinate in the same order as the request.",
            ),
        ]

        super().__init__(routes, config, logger, authenticator, auth_enabled=auth_enabled)
