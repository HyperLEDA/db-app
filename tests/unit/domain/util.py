import random
from math import pi

import astropy.units as u
from astropy.coordinates import ICRS, Angle, angular_separation

from app import entities
from app.data.repositories.layer2_repository import Layer2Repository
from app.domain.cross_id_simultaneous_data_provider import CrossIdSimultaneousDataProvider
from app.domain.model.params import cross_identification_result as result
from app.domain.model.params.cross_identification_user_param import CrossIdentificationUserParam


def make_points(
    n_points: int,
    center: ICRS,
    r: Angle,
) -> tuple[list[entities.ObjectInfo], list[entities.ObjectInfo]]:
    ra = [2 * pi * random.random() for _ in range(n_points)]
    dec = [pi * random.random() - pi / 2 for _ in range(n_points)]
    all_pts = [
        entities.ObjectInfo(None, None, ICRS(ra=it[0] * u.rad, dec=it[1] * u.rad)) for it in zip(ra, dec, strict=False)
    ]

    inside = [
        it for it in all_pts if angular_separation(it.coordinates.ra, it.coordinates.dec, center.ra, center.dec) <= r
    ]

    return all_pts, inside


def noop_cross_identify_function(
    layer2_repo: Layer2Repository,
    param: entities.ObjectInfo,
    simultaneous_data_provider: CrossIdSimultaneousDataProvider,
    user_param: CrossIdentificationUserParam,
) -> result.CrossIdentifyResult:
    return result.CrossIdentifyResult(None, None)
