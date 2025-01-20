import abc
import enum
from dataclasses import dataclass

import aiohttp
import aiohttp.typedefs
import aiohttp.web
import marshmallow


class HTTPMethod(enum.Enum):
    GET = "GET"
    POST = "POST"
    # add more if needed


@dataclass
class RouteInfo:
    method: HTTPMethod
    endpoint: str
    request_schema: type[marshmallow.Schema]
    response_schema: type[marshmallow.Schema]


class Route(abc.ABC):
    @abc.abstractmethod
    def request_schema(self) -> type[marshmallow.Schema]:
        """
        Returns schema for the request.
        """

    @abc.abstractmethod
    def response_schema(self) -> type[marshmallow.Schema]:
        """
        Returns schema for the response.
        """

    @abc.abstractmethod
    def method(self) -> str:
        """
        Returns HTTP method of the route.
        """

    @abc.abstractmethod
    def path(self) -> str:
        """
        Returns path of the route.
        """

    @abc.abstractmethod
    def handler(self) -> aiohttp.typedefs.Handler:
        """
        Returns handler of the route.
        """
