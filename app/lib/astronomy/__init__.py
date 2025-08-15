import numpy as np
from astropy import units as u


def velocity_wr_apex(
    vel: u.Quantity[u.Unit("km/s")],
    lon: u.Quantity[u.Unit("deg")],
    lat: u.Quantity[u.Unit("deg")],
    vel_apex: u.Quantity[u.Unit("km/s")],
    lon_apex: u.Quantity[u.Unit("deg")],
    lat_apex: u.Quantity[u.Unit("deg")],
) -> u.Quantity[u.Unit("km/s")]:
    """
    Computes velocity of an object with respect to a given apex.

    Parameters:
        vel: The observed velocity of the object.
        lon, lat: Galactic coordinates of an object.
        vel_apex: The velocity of the apex.
        lon_apexlat_apex: Galactic coordinates of the apex object.

    Returns:
        The velocity of the object with respect to the apex (in km/s).
    """
    return u.Quantity(
        vel - vel_apex * (np.sin(lat) * np.sin(lat_apex) + np.cos(lat) * np.cos(lat_apex) * np.cos(lon - lon_apex)),
    )
