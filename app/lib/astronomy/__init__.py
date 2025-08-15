import warnings

from astropy import units as u
from uncertainties import ufloat
from uncertainties.umath import cos, sin  # type: ignore

warnings.filterwarnings("ignore", message="Using UFloat objects with std_dev==0 may give unexpected results")


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

    vel_err_val = vel_err.to(u.Unit("km/s")).value if vel_err is not None else 0.0
    lon_err_val = lon_err.to(u.Unit("rad")).value if lon_err is not None else 0.0
    lat_err_val = lat_err.to(u.Unit("rad")).value if lat_err is not None else 0.0
    vel_apex_err_val = vel_apex_err.to(u.Unit("km/s")).value if vel_apex_err is not None else 0.0
    lon_apex_err_val = lon_apex_err.to(u.Unit("rad")).value if lon_apex_err is not None else 0.0
    lat_apex_err_val = lat_apex_err.to(u.Unit("rad")).value if lat_apex_err is not None else 0.0

    vel_u = ufloat(vel.value, vel_err_val)
    lon_u = ufloat(lon.value, lon_err_val)
    lat_u = ufloat(lat.value, lat_err_val)
    vel_apex_u = ufloat(vel_apex.value, vel_apex_err_val)
    lon_apex_u = ufloat(lon_apex.value, lon_apex_err_val)
    lat_apex_u = ufloat(lat_apex.value, lat_apex_err_val)

    result = vel_u - vel_apex_u * (
        sin(lat_u) * sin(lat_apex_u) + cos(lat_u) * cos(lat_apex_u) * cos(lon_u - lon_apex_u)  # type: ignore
    )

    return u.Quantity(result.nominal_value, unit="km/s"), u.Quantity(result.std_dev, unit="km/s")
