import warnings
from typing import Any

import numpy as np
import pytest
from astropy import units as u
from uncertainties import ufloat

from app.lib import astronomy


@pytest.fixture(autouse=True)
def ignore_ufloat_zero_std_dev_warning() -> None:
    warnings.filterwarnings("ignore", message="Using UFloat objects with std_dev==0 may give unexpected results")


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
    result = astronomy.velocity_wr_apex(
        vel=vel * u.Unit("km/s"),
        lon=lon * u.Unit("deg"),
        lat=lat * u.Unit("deg"),
        vel_apex=vel_apex * u.Unit("km/s"),
        lon_apex=lon_apex * u.Unit("deg"),
        lat_apex=lat_apex * u.Unit("deg"),
    )

    assert isinstance(result, tuple)
    assert len(result) == 2
    velocity, velocity_err = result

    assert velocity.value == pytest.approx(expected_vel, abs=1e-5)
    assert velocity_err.value == 0.0
    assert velocity.unit == u.Unit("km/s")
    assert velocity_err.unit == u.Unit("km/s")


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
    result = astronomy.velocity_wr_apex(
        vel=vel.nominal_value * u.Unit("km/s"),
        vel_err=vel.std_dev * u.Unit("km/s"),
        lon=lon.nominal_value * u.Unit("deg"),
        lon_err=lon.std_dev * u.Unit("deg"),
        lat=lat.nominal_value * u.Unit("deg"),
        lat_err=lat.std_dev * u.Unit("deg"),
        vel_apex=vel_apex.nominal_value * u.Unit("km/s"),
        vel_apex_err=vel_apex.std_dev * u.Unit("km/s"),
        lon_apex=lon_apex.nominal_value * u.Unit("deg"),
        lon_apex_err=lon_apex.std_dev * u.Unit("deg"),
        lat_apex=lat_apex.nominal_value * u.Unit("deg"),
        lat_apex_err=lat_apex.std_dev * u.Unit("deg"),
    )

    assert isinstance(result, tuple)
    assert len(result) == 2
    velocity, velocity_err = result

    assert velocity.value == pytest.approx(expected.nominal_value, abs=1e-5)
    assert velocity_err.value == pytest.approx(expected.std_dev, abs=1e-5)
    assert velocity.unit == u.Unit("km/s")
    assert velocity_err.unit == u.Unit("km/s")


def test_to_dimensionless_quantity() -> None:
    z = astronomy.to((4195.0 * u.Unit("km/s")) / astronomy.const("c"))
    assert z == pytest.approx(0.013993013793562478)


def test_parse_coordinate_epoch_invalid() -> None:
    with pytest.raises(ValueError, match="Invalid coordinate epoch"):
        astronomy.parse_coordinate_epoch("not-an-epoch")
