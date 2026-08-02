import unittest
import warnings

import numpy as np
from astropy import coordinates as coords
from astropy import units as u
from astropy.time import Time
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
        _: str,
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
        _: str,
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

    def test_to_dimensionless_quantity(self):
        z = astronomy.to((4195.0 * u.Unit("km/s")) / astronomy.const("c"))
        self.assertAlmostEqual(z, 0.013993013793562478)

    def test_equatorial_to_icrs_j2000_passthrough(self):
        ra, dec = 187.70593, 12.39112
        self.assertEqual(astronomy.equatorial_to_icrs(ra, dec), (ra, dec))
        self.assertEqual(astronomy.equatorial_to_icrs(ra, dec, "j2000"), (ra, dec))
        self.assertEqual(astronomy.equatorial_to_icrs(ra, dec, "J2000.0"), (ra, dec))

    def test_equatorial_to_icrs_b1950_roundtrip(self):
        ra_j2000, dec_j2000 = 187.70593, 12.39112
        b1950 = coords.SkyCoord(
            ra=ra_j2000 * u.Unit("deg"),
            dec=dec_j2000 * u.Unit("deg"),
            frame="icrs",
        ).transform_to(coords.FK5(equinox=Time("B1950")))

        ra_icrs, dec_icrs = astronomy.equatorial_to_icrs(float(b1950.ra.deg), float(b1950.dec.deg), "B1950")
        self.assertAlmostEqual(ra_icrs, ra_j2000, places=5)
        self.assertAlmostEqual(dec_icrs, dec_j2000, places=5)

    def test_parse_coordinate_epoch_invalid(self):
        with self.assertRaisesRegex(ValueError, "Invalid coordinate epoch"):
            astronomy.parse_coordinate_epoch("not-an-epoch")

    def test_galactic_to_icrs_roundtrip(self):
        ra_j2000, dec_j2000 = 187.70593, 12.39112
        galactic = coords.SkyCoord(
            ra=ra_j2000 * u.Unit("deg"),
            dec=dec_j2000 * u.Unit("deg"),
            frame="icrs",
        ).galactic

        ra_icrs, dec_icrs = astronomy.galactic_to_icrs(float(galactic.l.deg), float(galactic.b.deg))
        self.assertAlmostEqual(ra_icrs, ra_j2000, places=5)
        self.assertAlmostEqual(dec_icrs, dec_j2000, places=5)
