from typing import Any

import numpy as np
import pytest
from astropy import units as u
from uncertainties import ufloat

from app.lib import astronomy


@pytest.mark.parametrize(
    "vel,lon,lat,vel_apex,lon_apex,lat_apex,expected_vel",
    [
        pytest.param(100, 147, 50, 40, 147, 50, 140, id="apex and object in the same spot"),
        pytest.param(100, 147, 0, 40, 147, 90, 100, id="apex and object are perpendicular"),
        pytest.param(
            100,
            147,
            45,
            40,
            147,
            90,
            100 + 40 / np.sqrt(2),
            id="apex and object are angled",
        ),
        pytest.param(
            100,
            147,
            45,
            40,
            147,
            -90,
            100 - 40 / np.sqrt(2),
            id="apex and object are angled oppositely",
        ),
        pytest.param(100, 147, 45, 0, 147, -90, 100, id="apex is zero"),
    ],
)
def test_apex_velocity(
    vel: float,
    lon: float,
    lat: float,
    vel_apex: float,
    lon_apex: float,
    lat_apex: float,
    expected_vel: float,
) -> None:
    velocity, velocity_err = astronomy.velocity_wr_apex_batch(
        np.array([vel]),
        np.deg2rad(np.array([lon])),
        np.deg2rad(np.array([lat])),
        vel_apex,
        float(np.deg2rad(lon_apex)),
        float(np.deg2rad(lat_apex)),
        np.array([0.0]),
        np.array([0.0]),
        np.array([0.0]),
        0.0,
        0.0,
        0.0,
    )

    assert velocity[0] == pytest.approx(expected_vel, abs=1e-5)
    assert velocity_err[0] == 0.0


@pytest.mark.parametrize(
    "vel,lon,lat,vel_apex,lon_apex,lat_apex,expected",
    [
        pytest.param(
            ufloat(100, 5),
            ufloat(147, 0),
            ufloat(50, 0),
            ufloat(40, 0),
            ufloat(147, 0),
            ufloat(50, 0),
            ufloat(140, 5),
            id="with velocity uncertainty only",
        ),
        pytest.param(
            ufloat(100, 5),
            ufloat(147, 1),
            ufloat(50, 1),
            ufloat(40, 3),
            ufloat(147, 1),
            ufloat(50, 1),
            ufloat(140, 5.8309518),
            id="with all uncertainties",
        ),
    ],
)
def test_apex_velocity_with_uncertainties(
    vel: Any,
    lon: Any,
    lat: Any,
    vel_apex: Any,
    lon_apex: Any,
    lat_apex: Any,
    expected: Any,
) -> None:
    velocity, velocity_err = astronomy.velocity_wr_apex_batch(
        np.array([vel.nominal_value]),
        np.deg2rad(np.array([lon.nominal_value])),
        np.deg2rad(np.array([lat.nominal_value])),
        vel_apex.nominal_value,
        float(np.deg2rad(lon_apex.nominal_value)),
        float(np.deg2rad(lat_apex.nominal_value)),
        np.array([vel.std_dev]),
        np.deg2rad(np.array([lon.std_dev])),
        np.deg2rad(np.array([lat.std_dev])),
        vel_apex.std_dev,
        float(np.deg2rad(lon_apex.std_dev)),
        float(np.deg2rad(lat_apex.std_dev)),
    )

    assert velocity[0] == pytest.approx(expected.nominal_value, abs=1e-5)
    assert velocity_err[0] == pytest.approx(expected.std_dev, abs=1e-5)


def test_to_dimensionless_quantity() -> None:
    z = astronomy.to((4195.0 * u.Unit("km/s")) / astronomy.const("c"))
    assert z == pytest.approx(0.013993013793562478)


def test_parse_coordinate_epoch_invalid() -> None:
    with pytest.raises(ValueError, match="Invalid coordinate epoch"):
        astronomy.parse_coordinate_epoch("not-an-epoch")
