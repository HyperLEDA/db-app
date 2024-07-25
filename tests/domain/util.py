import random
from math import pi

import astropy.units as u
from astropy.coordinates import ICRS, Angle, angular_separation

from app.domain.cross_id_simultaneous_data_provider import CrossIdSimultaneousDataProvider
from app.domain.model.params import CrossIdentificationParam
from app.domain.model.params import cross_identification_result as result
from app.domain.model.params.cross_dentification_user_param import CrossIdentificationUserParam
from app.domain.usecases import CrossIdentifyUseCase


def make_points(
    n_points: int,
    center: ICRS,
    r: Angle,
) -> tuple[list[CrossIdentificationParam], list[CrossIdentificationParam]]:
    ra = [2 * pi * random.random() for _ in range(n_points)]
    dec = [pi * random.random() - pi / 2 for _ in range(n_points)]
    all_pts = [CrossIdentificationParam(None, None, ICRS(ra=it[0] * u.rad, dec=it[1] * u.rad)) for it in zip(ra, dec)]

    inside = [
        it for it in all_pts if angular_separation(it.coordinates.ra, it.coordinates.dec, center.ra, center.dec) <= r
    ]

    return all_pts, inside


class MockedCrossIdentifyUseCase(CrossIdentifyUseCase):
    def __init__(self):
        pass

    async def invoke(
        self,
        param: CrossIdentificationParam,
        simultaneous_data_provider: CrossIdSimultaneousDataProvider,
        user_param: CrossIdentificationUserParam,
    ) -> result.CrossIdentifyResult | result.CrossIdentificationException:
        return result.CrossIdentifyResult(None, None)
