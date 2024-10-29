from abc import ABC, abstractmethod
from math import acos, cos, sin

import astropy.units as u
from astropy.coordinates import ICRS, Angle
from pandas import DataFrame

from app import entities
from app.domain.model.params import TmpCoordinateTableQueryParam, TmpNameTableQueryParam
from app.domain.repositories.tmp_data_repository import TmpDataRepository


def _sph_dist(a: ICRS, b: ICRS) -> Angle:
    a_ra = a.ra.to(u.rad).value
    a_dec = a.dec.to(u.rad).value
    b_ra = b.ra.to(u.rad).value
    b_dec = b.dec.to(u.rad).value
    return acos(sin(b_dec) * sin(a_dec) + cos(b_dec) * cos(a_dec) * cos(b_ra - a_ra)) * u.rad


class CrossIdSimultaneousDataProvider(ABC):
    """
    Used to access currently processing data from cross identification action.
    We must cross identify not only objects that are already in the DB
    but also currently processed objects
    """

    def __init__(self, data: list[entities.ObjectInfo]):
        self._data: list[entities.ObjectInfo] = data

    @abstractmethod
    def data_inside(self, center: ICRS, r: Angle) -> list[entities.ObjectInfo]:
        """
        Get all points around given point

        :param center: Target point
        :param r: Radius around center, represented in angle
        :return: Points in given circle
        """

    @abstractmethod
    def by_name(self, names: list[str]) -> list[entities.ObjectInfo]:
        """
        Select items by names

        :param names: All known names in raw table
        :return: Items with matching name
        """

    def clear(self):
        """Used to free used resources"""


class SimpleSimultaneousDataProvider(CrossIdSimultaneousDataProvider):
    def data_inside(self, center: ICRS, r: Angle) -> list[entities.ObjectInfo]:
        return [
            it
            for it in self._data
            if it.coordinates is not None
            and center.dec - r <= it.coordinates.dec <= center.dec + r
            and _sph_dist(it.coordinates, center) < r
        ]

    def by_name(self, names: list[str]) -> list[entities.ObjectInfo]:
        names_set = set(names)
        return [it for it in self._data if len(set(it.names or []) & names_set) > 0]


class PostgreSimultaneousDataProvider(CrossIdSimultaneousDataProvider):
    def __init__(self, data: list[entities.ObjectInfo], tmp_data_repository: TmpDataRepository):
        super().__init__(data)
        self._tmp_data_repository = tmp_data_repository
        self.table_name: str = tmp_data_repository.make_table(
            DataFrame(
                {
                    "idx": list(range(len(data))),
                    "name": [it.names for it in data],
                    "ra": [it.coordinates.ra.to(u.deg).value if it.coordinates is not None else None for it in data],
                    "dec": [it.coordinates.dec.to(u.deg).value if it.coordinates is not None else None for it in data],
                }
            ),
            index_on=["ra", "dec"],
        )

    def data_inside(self, center: ICRS, r: Angle) -> list[entities.ObjectInfo]:
        res = self._tmp_data_repository.query_table(TmpCoordinateTableQueryParam(self.table_name, center, r))
        return [self._data[it["idx"]] for it in res]

    def by_name(self, names: list[str]) -> list[entities.ObjectInfo]:
        res = self._tmp_data_repository.query_table(TmpNameTableQueryParam(self.table_name, names))

        return [self._data[it["idx"]] for it in res]

    def clear(self):
        self._tmp_data_repository.drop_table(self.table_name)
