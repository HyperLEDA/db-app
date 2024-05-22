from abc import ABC, abstractmethod
import astropy.units as u
from astropy.coordinates import Angle, ICRS
from math import acos, sin, cos
import asyncio
from astropy import units as u

from pandas import DataFrame

from app.domain.model.params import CrossIdentificationParam, TmpCoordinateTableQueryParam
from sklearn.neighbors import BallTree
import numpy as np

from app.domain.repositories.tmp_data_repository import TmpDataRepository


class CrossIdSimultaneousDataProvider(ABC):
    """
    Used to access currently processing data from CrossIdentifyUseCase. We must cross identify not only objects,
    that are already in the DB, but also currently processed objects
    """
    def __init__(self, data: list[CrossIdentificationParam]):
        self._data: list[CrossIdentificationParam] = data

    @abstractmethod
    def data_inside(self, center: ICRS, r: Angle) -> list[CrossIdentificationParam]:
        """
        Get all points around given point
        :param center: Target point
        :param r: Radius around center, represented in angle
        :return: Points in given circle
        """
        pass

    def clear(self):
        """Used to free used resources"""
        pass


class KDTreeSimultaneousDataProvider(CrossIdSimultaneousDataProvider):
    def __init__(self, data: list[CrossIdentificationParam]):
        super().__init__(data)
        self._tree: BallTree = BallTree(
            np.array([[it.coordinates.dec.to(u.rad).value, it.coordinates.ra.to(u.rad).value] for it in data]),
            metric='haversine'
        )

    def data_inside(self, center: ICRS, r: Angle) -> list[CrossIdentificationParam]:
        ind,  = self._tree.query_radius(np.array([[center.dec.to(u.rad).value, center.ra.to(u.rad).value]]), r.to(u.rad).value)
        return list(np.array(self._data)[ind])


class SimpleSimultaneousDataProvider(CrossIdSimultaneousDataProvider):
    def data_inside(self, center: ICRS, r: Angle) -> list[CrossIdentificationParam]:
        return [
            it for
            it in self._data
            if it.coordinates is not None
            and center.dec - r <= it.coordinates.dec <= center.dec + r
            and self._sph_dist(it.coordinates, center) < r
        ]

    @staticmethod
    def _sph_dist(a: ICRS, b: ICRS) -> Angle:
        a_ra = a.ra.to(u.rad).value
        a_dec = a.dec.to(u.rad).value
        b_ra = b.ra.to(u.rad).value
        b_dec = b.dec.to(u.rad).value
        return acos(
            sin(b_dec) * sin(a_dec) +
            cos(b_dec) * cos(a_dec) * cos(b_ra - a_ra)
        ) * u.rad


class PostgreSimultaneousDataProvider(CrossIdSimultaneousDataProvider):
    def __init__(self, data: list[CrossIdentificationParam], tmp_data_repository: TmpDataRepository):
        super().__init__(data)
        self._tmp_data_repository = tmp_data_repository
        task = tmp_data_repository.make_table(DataFrame({
            "idx": list(range(0, len(data))),
            "name": [it.name for it in data],
            "ra": [it.coordinates.ra.to(u.deg).value for it in data],
            "dec": [it.coordinates.dec.to(u.deg).value for it in data]
        }), index_on=["ra", "dec"])
        self._table_name: str = asyncio.run(task)

    def data_inside(self, center: ICRS, r: Angle) -> list[CrossIdentificationParam]:
        res = asyncio.run(
            self._tmp_data_repository.query_table(TmpCoordinateTableQueryParam(self._table_name, center, r))
        )
        return [
            self._data[it["idx"]]
            for it in res
        ]

    def clear(self):
        asyncio.run(self._tmp_data_repository.drop_table(self._table_name))
    