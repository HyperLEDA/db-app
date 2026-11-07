import warnings
from typing import Literal

import numpy as np
from astropy import constants
from astropy import coordinates as coords
from astropy import units as u
from astropy.time import Time
from uncertainties import ufloat
from uncertainties.umath import cos, sin

warnings.filterwarnings("ignore", message="Using UFloat objects with std_dev==0 may give unexpected results")

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
    coord = coords.SkyCoord(ra=ra * u.Unit("deg"), dec=dec * u.Unit("deg"))
    transformed = coord.transform_to(frame)
    lon = to(transformed.spherical.lon, "deg")
    lat = to(transformed.spherical.lat, "deg")
    # for simplicity this approach assumes errors in the transformed coordinates to be the
    # same, which might not necessarily be true for larger errors.
    e_lon = to(e_ra * u.Unit("deg"), "arcsec")
    e_lat = to(e_dec * u.Unit("deg"), "arcsec")
    return lon, lat, e_lon, e_lat


def equatorial_to_galactic_radians(ra: np.ndarray, dec: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    transformed = coords.SkyCoord(ra=ra * u.Unit("deg"), dec=dec * u.Unit("deg")).transform_to("galactic")
    return _quantity_values(transformed.spherical.lon, "rad"), _quantity_values(transformed.spherical.lat, "rad")


def _quantity_values(value: u.Quantity, unit: str) -> np.ndarray:
    return np.asarray(value.to(u.Unit(unit)).value, dtype=float)


def velocity_wr_apex(
    vel: u.Quantity[u.Unit("km/s")],
    lon: u.Quantity[u.Unit("deg")],
    lat: u.Quantity[u.Unit("deg")],
    vel_apex: u.Quantity[u.Unit("km/s")],
    lon_apex: u.Quantity[u.Unit("deg")],
    lat_apex: u.Quantity[u.Unit("deg")],
    vel_err: u.Quantity[u.Unit("km/s")] | None = None,
    lon_err: u.Quantity[u.Unit("deg")] | None = None,
    lat_err: u.Quantity[u.Unit("deg")] | None = None,
    vel_apex_err: u.Quantity[u.Unit("km/s")] | None = None,
    lon_apex_err: u.Quantity[u.Unit("deg")] | None = None,
    lat_apex_err: u.Quantity[u.Unit("deg")] | None = None,
) -> tuple[u.Quantity[u.Unit("km/s")], u.Quantity[u.Unit("km/s")]]:
    """
    Computes velocity of an object with respect to a given apex.

    Parameters:
        vel: The observed velocity of the object.
        lon, lat: Galactic coordinates of an object.
        vel_apex: The velocity of the apex.
        lon_apex, lat_apex: Galactic coordinates of the apex object.
        vel_err: Uncertainty in the observed velocity of the object.
        lon_err, lat_err: Uncertainties in galactic coordinates of an object.
        vel_apex_err: Uncertainty in the velocity of the apex.
        lon_apex_err, lat_apex_err: Uncertainties in galactic coordinates of the apex object.

    Returns:
        A tuple containing (velocity, velocity_uncertainty) in km/s.
        If no error parameters are provided, the uncertainty will be zero.
    """
    vel = vel.to(u.Unit("km/s"))
    lon = lon.to(u.Unit("rad"))
    lat = lat.to(u.Unit("rad"))
    vel_apex = vel_apex.to(u.Unit("km/s"))
    lon_apex = lon_apex.to(u.Unit("rad"))
    lat_apex = lat_apex.to(u.Unit("rad"))

    vel_err_val = to(vel_err, "km/s") if vel_err is not None else 0.0
    lon_err_val = to(lon_err, "rad") if lon_err is not None else 0.0
    lat_err_val = to(lat_err, "rad") if lat_err is not None else 0.0
    vel_apex_err_val = to(vel_apex_err, "km/s") if vel_apex_err is not None else 0.0
    lon_apex_err_val = to(lon_apex_err, "rad") if lon_apex_err is not None else 0.0
    lat_apex_err_val = to(lat_apex_err, "rad") if lat_apex_err is not None else 0.0

    vel_u = ufloat(vel.value, vel_err_val)
    lon_u = ufloat(lon.value, lon_err_val)
    lat_u = ufloat(lat.value, lat_err_val)
    vel_apex_u = ufloat(vel_apex.value, vel_apex_err_val)
    lon_apex_u = ufloat(lon_apex.value, lon_apex_err_val)
    lat_apex_u = ufloat(lat_apex.value, lat_apex_err_val)

    result = vel_u + vel_apex_u * (
        sin(lat_u) * sin(lat_apex_u) + cos(lat_u) * cos(lat_apex_u) * cos(lon_u - lon_apex_u)
    )

    return u.Quantity(result.nominal_value, unit="km/s"), u.Quantity(result.std_dev, unit="km/s")


def velocity_wr_apex_batch(
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
