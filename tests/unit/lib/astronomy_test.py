import unittest
import warnings

import numpy as np
from astropy import units as u
from parameterized import param, parameterized
from uncertainties import ufloat

from app.lib import astronomy


class AstronomyTest(unittest.TestCase):
    def setUp(self):
        warnings.filterwarnings("ignore", message="Using UFloat objects with std_dev==0 may give unexpected results")

    @parameterized.expand(
        [
            param(
                "apex and object in the same spot",
                vel=100,
                lon=147,
                lat=50,
                vel_apex=40,
                lon_apex=147,
                lat_apex=50,
                expected_vel=60,
            ),
            param(
                "apex and object are perpendicular",
                vel=100,
                lon=147,
                lat=0,
                vel_apex=40,
                lon_apex=147,
                lat_apex=90,
                expected_vel=100,
            ),
            param(
                "apex and object are angled",
                vel=100,
                lon=147,
                lat=45,
                vel_apex=40,
                lon_apex=147,
                lat_apex=90,
                expected_vel=100 - 40 / np.sqrt(2),
            ),
            param(
                "apex and object are angled oppositely",
                vel=100,
                lon=147,
                lat=45,
                vel_apex=40,
                lon_apex=147,
                lat_apex=-90,
                expected_vel=100 + 40 / np.sqrt(2),
            ),
            param("apex is zero", vel=100, lon=147, lat=45, vel_apex=0, lon_apex=147, lat_apex=-90, expected_vel=100),
        ]
    )
    def test_apex_velocity(
        self,
        name: str,
        vel: float,
        lon: float,
        lat: float,
        vel_apex: float,
        lon_apex: float,
        lat_apex: float,
        expected_vel: float,
    ):
        result = astronomy.velocity_wr_apex(
            vel=vel * u.Unit("km/s"),
            lon=lon * u.Unit("deg"),
            lat=lat * u.Unit("deg"),
            vel_apex=vel_apex * u.Unit("km/s"),
            lon_apex=lon_apex * u.Unit("deg"),
            lat_apex=lat_apex * u.Unit("deg"),
        )

        self.assertIsInstance(result, tuple)
        self.assertEqual(len(result), 2)
        velocity, velocity_err = result

        self.assertAlmostEqual(velocity.value, expected_vel, places=5)
        self.assertEqual(velocity_err.value, 0.0)
        self.assertEqual(velocity.unit, u.Unit("km/s"))
        self.assertEqual(velocity_err.unit, u.Unit("km/s"))

    @parameterized.expand(
        [
            param(
                "with velocity uncertainty only",
                vel=ufloat(100, 5),
                lon=ufloat(147, 0),
                lat=ufloat(50, 0),
                vel_apex=ufloat(40, 0),
                lon_apex=ufloat(147, 0),
                lat_apex=ufloat(50, 0),
                expected=ufloat(60, 5),
            ),
            param(
                "with all uncertainties",
                vel=ufloat(100, 5),
                lon=ufloat(147, 1),
                lat=ufloat(50, 1),
                vel_apex=ufloat(40, 3),
                lon_apex=ufloat(147, 1),
                lat_apex=ufloat(50, 1),
                expected=ufloat(60, 5.8309518),
            ),
        ]
    )
    def test_apex_velocity_with_uncertainties(
        self,
        name: str,
        vel,
        lon,
        lat,
        vel_apex,
        lon_apex,
        lat_apex,
        expected,
    ):
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

        self.assertIsInstance(result, tuple)
        self.assertEqual(len(result), 2)
        velocity, velocity_err = result

        self.assertAlmostEqual(velocity.value, expected.nominal_value, places=5)
        self.assertAlmostEqual(velocity_err.value, expected.std_dev, places=5)
        self.assertEqual(velocity.unit, u.Unit("km/s"))
        self.assertEqual(velocity_err.unit, u.Unit("km/s"))
