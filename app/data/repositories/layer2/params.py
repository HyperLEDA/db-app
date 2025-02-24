import abc
from typing import Any, final


class SearchParams(abc.ABC):
    @abc.abstractmethod
    def name() -> str:
        pass

    @abc.abstractmethod
    def get_params(self) -> dict[str, Any]:
        pass


@final
class ICRSSearchParams(SearchParams):
    def name(self) -> str:
        return "icrs"

    def __init__(self, ra: float, dec: float):
        self._ra = ra
        self._dec = dec

    def get_params(self) -> dict[str, Any]:
        return {"ra": self._ra, "dec": self._dec}


@final
class DesignationSearchParams(SearchParams):
    def __init__(self, designation: str):
        self._designation = designation

    def name(self) -> str:
        return "designation"

    def get_params(self) -> dict[str, Any]:
        return {"design": self._designation}


@final
class CombinedSearchParams(SearchParams):
    def __init__(self, params: list[SearchParams]):
        self._params = params

    def name(self) -> str:
        return "_".join([p.name() for p in self._params])

    def get_params(self) -> dict[str, Any]:
        res = {}

        for p in self._params:
            res.update(p.get_params())

        return res
