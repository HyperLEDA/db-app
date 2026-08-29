import abc
from typing import Any, final, override

from astropy import coordinates as coords
from astropy import units as u

from app.lib import astronomy


class SearchParams(abc.ABC):
    @abc.abstractmethod
    def name(self) -> str:
        pass

    @abc.abstractmethod
    def get_params(self) -> dict[str, Any]:
        pass


@final
class ICRSSearchParams(SearchParams):
    @override
    def name(self) -> str:
        return "icrs"

    def __init__(
        self,
        ra: u.Quantity | None = None,
        dec: u.Quantity | None = None,
        coords: coords.SkyCoord | None = None,
    ):
        if coords is not None:
            ra = coords.ra
            dec = coords.dec
        if ra is None or dec is None:
            raise ValueError("ra and dec are required when coords is not provided")

        self._ra = astronomy.to(ra, "deg")
        self._dec = astronomy.to(dec, "deg")

    def get_params(self) -> dict[str, Any]:
        return {"ra": self._ra, "dec": self._dec}


@final
class DesignationSearchParams(SearchParams):
    def __init__(self, designation: str):
        self._designation = designation

    @override
    def name(self) -> str:
        return "designation"

    def get_params(self) -> dict[str, Any]:
        return {"design": self._designation}


@final
class CombinedSearchParams(SearchParams):
    def __init__(self, params: list[SearchParams]):
        self._params = params

    def name(self) -> str:
        return "_".join([p.name() for p in self._params]) or "combined"

    def get_params(self) -> dict[str, Any]:
        res = {}

        for p in self._params:
            res.update(p.get_params())

        return res
