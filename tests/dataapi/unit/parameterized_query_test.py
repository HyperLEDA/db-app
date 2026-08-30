import unittest
from unittest import mock

from astropy import coordinates as coords
from astropy import units as u
from astropy.time import Time

from app import catalogs
from app.dataapi.domain import parameterized_query
from app.lib.web import errors
from app.specs import dataapi

DEFAULT = [
    catalogs.RawCatalog.DESIGNATION,
    catalogs.RawCatalog.ICRS,
    catalogs.RawCatalog.REDSHIFT,
]


class ResolveQueryCatalogsTest(unittest.TestCase):
    def test_none_returns_default(self):
        self.assertEqual(
            parameterized_query.resolve_query_catalogs(None, DEFAULT),
            DEFAULT,
        )

    def test_subset_preserves_request_order(self):
        self.assertEqual(
            parameterized_query.resolve_query_catalogs(
                ["icrs", "designation"],
                DEFAULT,
            ),
            [catalogs.RawCatalog.ICRS, catalogs.RawCatalog.DESIGNATION],
        )

    def test_deduplicates(self):
        self.assertEqual(
            parameterized_query.resolve_query_catalogs(
                ["icrs", "icrs"],
                DEFAULT,
            ),
            [catalogs.RawCatalog.ICRS],
        )

    def test_empty_list_raises(self):
        with self.assertRaisesRegex(errors.RuleValidationError, "must not be empty"):
            parameterized_query.resolve_query_catalogs([], DEFAULT)

    def test_unknown_catalog_raises(self):
        with self.assertRaisesRegex(errors.RuleValidationError, "Unknown catalog"):
            parameterized_query.resolve_query_catalogs(["not_a_catalog"], DEFAULT)

    def test_unavailable_catalog_raises(self):
        with self.assertRaisesRegex(errors.RuleValidationError, "not available"):
            parameterized_query.resolve_query_catalogs(
                ["note"],
                DEFAULT,
            )


class QuerySimpleDispatchTest(unittest.TestCase):
    def setUp(self) -> None:
        self.repo = mock.Mock()
        self.repo.query_catalogs.return_value = []
        self.repo.find_pgcs_by_designation.return_value = []
        self.repo.find_pgcs_by_equatorial.return_value = []
        self.repo.find_pgcs_unfiltered.return_value = []
        self.manager = parameterized_query.ParameterizedQueryManager(
            repo=self.repo,
            enabled_catalogs=DEFAULT,
            catalog_cfg=mock.Mock(),
            reddening_service=mock.Mock(),
        )

    def test_coordinate_search_calls_equatorial_finder(self):
        ra_fk5, dec_fk5 = 10.0, 20.0
        expected = coords.SkyCoord(
            ra=ra_fk5 * u.Unit("deg"),
            dec=dec_fk5 * u.Unit("deg"),
            frame=coords.FK5(equinox=Time("J2000")),
        ).transform_to("icrs")

        query = dataapi.QuerySimpleRequest(ra=ra_fk5, dec=dec_fk5, radius=0.1)
        with mock.patch("app.dataapi.responders.StructuredResponder") as responder_cls:
            responder_cls.return_value.build_response.return_value = mock.Mock()
            self.manager.query_simple(query)

        self.repo.find_pgcs_by_equatorial.assert_called_once()
        call = self.repo.find_pgcs_by_equatorial.call_args
        self.assertAlmostEqual(call.args[0], expected.ra.deg, places=10)
        self.assertAlmostEqual(call.args[1], expected.dec.deg, places=10)
        self.assertEqual(call.args[3], query.page_size)
        self.assertEqual(call.args[4], 0)

    def test_name_search_calls_designation_finder(self):
        query = dataapi.QuerySimpleRequest(name="NGC", page=2, page_size=25)
        with mock.patch("app.dataapi.responders.StructuredResponder") as responder_cls:
            responder_cls.return_value.build_response.return_value = mock.Mock()
            self.manager.query_simple(query)

        self.repo.find_pgcs_by_designation.assert_called_once_with("NGC", 25, 50)

    def test_pgc_filter_paginates_in_memory(self):
        query = dataapi.QuerySimpleRequest(pgcs=[3, 1, 2], page=1, page_size=1)
        with mock.patch("app.dataapi.responders.StructuredResponder") as responder_cls:
            responder_cls.return_value.build_response.return_value = mock.Mock()
            self.manager.query_simple(query)

        self.repo.find_pgcs_by_designation.assert_not_called()
        self.repo.find_pgcs_by_equatorial.assert_not_called()
        self.repo.query_catalogs.assert_called_once()
        self.assertEqual(self.repo.query_catalogs.call_args.args[1], [2])

    def test_coordinate_search_precesses_b1950(self):
        ra_j2000, dec_j2000 = 187.70593, 12.39112
        b1950 = coords.SkyCoord(
            ra=ra_j2000 * u.Unit("deg"),
            dec=dec_j2000 * u.Unit("deg"),
            frame="icrs",
        ).transform_to(coords.FK5(equinox=Time("B1950")))

        query = dataapi.QuerySimpleRequest(
            ra=float(b1950.ra.deg),
            dec=float(b1950.dec.deg),
            radius=0.1,
            eq_epoch="B1950",
        )
        with mock.patch("app.dataapi.responders.StructuredResponder") as responder_cls:
            responder_cls.return_value.build_response.return_value = mock.Mock()
            self.manager.query_simple(query)

        call = self.repo.find_pgcs_by_equatorial.call_args
        self.assertAlmostEqual(call.args[0], ra_j2000, places=5)
        self.assertAlmostEqual(call.args[1], dec_j2000, places=5)

    def test_galactic_coordinate_search_converts_to_icrs(self):
        ra_j2000, dec_j2000 = 187.70593, 12.39112
        galactic = coords.SkyCoord(
            ra=ra_j2000 * u.Unit("deg"),
            dec=dec_j2000 * u.Unit("deg"),
            frame="icrs",
        ).galactic

        query = dataapi.QuerySimpleRequest(
            glon=float(galactic.l.deg),
            glat=float(galactic.b.deg),
            radius=0.1,
        )
        with mock.patch("app.dataapi.responders.StructuredResponder") as responder_cls:
            responder_cls.return_value.build_response.return_value = mock.Mock()
            self.manager.query_simple(query)

        call = self.repo.find_pgcs_by_equatorial.call_args
        self.assertAlmostEqual(call.args[0], ra_j2000, places=5)
        self.assertAlmostEqual(call.args[1], dec_j2000, places=5)

    def test_supergalactic_coordinate_search_converts_to_icrs(self):
        ra_j2000, dec_j2000 = 187.70593, 12.39112
        sg = coords.SkyCoord(
            ra=ra_j2000 * u.Unit("deg"),
            dec=dec_j2000 * u.Unit("deg"),
            frame="icrs",
        ).supergalactic

        query = dataapi.QuerySimpleRequest(
            sgl=float(sg.sgl.deg),
            sgb=float(sg.sgb.deg),
            radius=0.1,
        )
        with mock.patch("app.dataapi.responders.StructuredResponder") as responder_cls:
            responder_cls.return_value.build_response.return_value = mock.Mock()
            self.manager.query_simple(query)

        call = self.repo.find_pgcs_by_equatorial.call_args
        self.assertAlmostEqual(call.args[0], ra_j2000, places=5)
        self.assertAlmostEqual(call.args[1], dec_j2000, places=5)

    def test_unfiltered_search_calls_unfiltered_finder(self):
        query = dataapi.QuerySimpleRequest(page=1, page_size=10)
        with mock.patch("app.dataapi.responders.StructuredResponder") as responder_cls:
            responder_cls.return_value.build_response.return_value = mock.Mock()
            self.manager.query_simple(query)

        self.repo.find_pgcs_unfiltered.assert_called_once_with(10, 10)

    def test_always_builds_response(self):
        query = dataapi.QuerySimpleRequest(name="NGC")
        with mock.patch("app.dataapi.responders.StructuredResponder") as responder_cls:
            responder_cls.return_value.build_response.return_value = mock.Mock()
            self.manager.query_simple(query)

        responder_cls.return_value.build_response.assert_called_once()
        responder_cls.return_value.build_response_from_catalog.assert_not_called()
