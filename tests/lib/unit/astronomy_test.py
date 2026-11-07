import numpy as np
import pytest
from astropy import units as u

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
    velocity, velocity_err = astronomy.velocity_wr_apex(
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
    "vel,e_vel,lon,e_lon,lat,e_lat,vel_apex,e_vel_apex,lon_apex,e_lon_apex,lat_apex,e_lat_apex,expected_vel,expected_err",
    [
        pytest.param(100, 5, 147, 0, 50, 0, 40, 0, 147, 0, 50, 0, 140, 5, id="with velocity uncertainty only"),
        pytest.param(
            100,
            5,
            147,
            1,
            50,
            1,
            40,
            3,
            147,
            1,
            50,
            1,
            140,
            5.8309518,
            id="with all uncertainties",
        ),
    ],
)
def test_apex_velocity_with_uncertainties(
    vel: float,
    e_vel: float,
    lon: float,
    e_lon: float,
    lat: float,
    e_lat: float,
    vel_apex: float,
    e_vel_apex: float,
    lon_apex: float,
    e_lon_apex: float,
    lat_apex: float,
    e_lat_apex: float,
    expected_vel: float,
    expected_err: float,
) -> None:
    velocity, velocity_err = astronomy.velocity_wr_apex(
        np.array([vel]),
        np.deg2rad(np.array([lon])),
        np.deg2rad(np.array([lat])),
        vel_apex,
        float(np.deg2rad(lon_apex)),
        float(np.deg2rad(lat_apex)),
        np.array([e_vel]),
        np.deg2rad(np.array([e_lon])),
        np.deg2rad(np.array([e_lat])),
        e_vel_apex,
        float(np.deg2rad(e_lon_apex)),
        float(np.deg2rad(e_lat_apex)),
    )

    assert velocity[0] == pytest.approx(expected_vel, abs=1e-5)
    assert velocity_err[0] == pytest.approx(expected_err, abs=1e-5)


def test_to_dimensionless_quantity() -> None:
    z = astronomy.to((4195.0 * u.Unit("km/s")) / astronomy.const("c"))
    assert z == pytest.approx(0.013993013793562478)


def test_parse_coordinate_epoch_invalid() -> None:
    with pytest.raises(ValueError, match="Invalid coordinate epoch"):
        astronomy.parse_coordinate_epoch("not-an-epoch")
