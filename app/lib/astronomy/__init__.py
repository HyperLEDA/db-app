from typing import Literal

import numpy as np
from astropy import constants
from astropy import coordinates as coords
from astropy import units as u
from astropy.time import Time

CoordinateFrame = Literal["galactic", "supergalactic"]


def const(const_name: str) -> u.Quantity:
    return getattr(constants, const_name)


def parse_coordinate_epoch(epoch: str) -> Time:
    try:
        return Time(epoch)
    except (ValueError, TypeError, OSError) as exc:
        raise ValueError(f"Invalid coordinate epoch {epoch!r}; expected an equinox like J2000 or B1950") from exc


def to(value: u.Quantity, unit: str | None = None) -> float:
    if unit is None:
        if value.unit.is_equivalent(u.one):
            return float(value.decompose().value)
        return value.value

    return float(value.to(u.Unit(unit)).value)


def heliocentric_cz_to_z(cz: u.Quantity[u.Unit("km/s")]) -> float:
    return to(cz / const("c"))


def equatorial_to_lonlat(
    ra: float,
    dec: float,
    e_ra: float,
    e_dec: float,
    frame: CoordinateFrame,
) -> tuple[float, float, float, float]:
    lon, lat = equatorial_to_lonlat_deg(np.asarray([ra], dtype=float), np.asarray([dec], dtype=float), frame)
    # for simplicity this approach assumes errors in the transformed coordinates to be the
    # same, which might not necessarily be true for larger errors.
    e_lon = to(e_ra * u.Unit("deg"), "arcsec")
    e_lat = to(e_dec * u.Unit("deg"), "arcsec")
    return float(lon[0]), float(lat[0]), e_lon, e_lat


def equatorial_to_lonlat_deg(
    ra: np.ndarray,
    dec: np.ndarray,
    frame: CoordinateFrame,
) -> tuple[np.ndarray, np.ndarray]:
    if len(ra) == 0:
        return np.asarray([], dtype=float), np.asarray([], dtype=float)
    transformed = coords.SkyCoord(ra=ra * u.Unit("deg"), dec=dec * u.Unit("deg")).transform_to(frame)
    return _quantity_values(transformed.spherical.lon, "deg"), _quantity_values(transformed.spherical.lat, "deg")


def equatorial_to_galactic_radians(ra: np.ndarray, dec: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    transformed = coords.SkyCoord(ra=ra * u.Unit("deg"), dec=dec * u.Unit("deg")).transform_to("galactic")
    return _quantity_values(transformed.spherical.lon, "rad"), _quantity_values(transformed.spherical.lat, "rad")


def _quantity_values(value: u.Quantity, unit: str) -> np.ndarray:
    return np.asarray(value.to(u.Unit(unit)).value, dtype=float)


def velocity_wr_apex(
    vel: np.ndarray,
    lon: np.ndarray,
    lat: np.ndarray,
    vel_apex: float,
    lon_apex: float,
    lat_apex: float,
    vel_err: np.ndarray,
    lon_err: np.ndarray,
    lat_err: np.ndarray,
    vel_apex_err: float,
    lon_apex_err: float,
    lat_apex_err: float,
) -> tuple[np.ndarray, np.ndarray]:
    separation = lon - lon_apex
    sin_lat = np.sin(lat)
    cos_lat = np.cos(lat)
    sin_lat_apex = np.sin(lat_apex)
    cos_lat_apex = np.cos(lat_apex)
    cos_separation = np.cos(separation)
    sin_separation = np.sin(separation)
    projection = sin_lat * sin_lat_apex + cos_lat * cos_lat_apex * cos_separation
    velocity = vel + vel_apex * projection
    d_lat = vel_apex * (cos_lat * sin_lat_apex - sin_lat * cos_lat_apex * cos_separation)
    d_lon = vel_apex * (-cos_lat * cos_lat_apex * sin_separation)
    d_lat_apex = vel_apex * (sin_lat * cos_lat_apex - cos_lat * sin_lat_apex * cos_separation)
    d_lon_apex = vel_apex * (cos_lat * cos_lat_apex * sin_separation)
    variance = (
        np.square(vel_err)
        + np.square(projection * vel_apex_err)
        + np.square(d_lat * lat_err)
        + np.square(d_lon * lon_err)
        + np.square(d_lat_apex * lat_apex_err)
        + np.square(d_lon_apex * lon_apex_err)
    )
    return velocity, np.sqrt(variance)
