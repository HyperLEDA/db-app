import unittest

import numpy as np
from astropy import units as u
from parameterized import param, parameterized

from app.lib import astronomy


class AstronomyTest(unittest.TestCase):
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
            param(
                "apex is zero",
                vel=100,
                lon=147,
                lat=45,
                vel_apex=0,
                lon_apex=147,
                lat_apex=-90,
                expected_vel=100,
            ),
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

        self.assertAlmostEqual(result.value, expected_vel, places=5)
