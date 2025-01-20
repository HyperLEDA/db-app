import abc

import aiohttp
import aiohttp.typedefs
import aiohttp.web
import marshmallow


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
