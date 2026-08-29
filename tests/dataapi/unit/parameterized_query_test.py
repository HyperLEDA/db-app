import unittest
from unittest import mock

from astropy import coordinates as coords
from astropy import units as u
from astropy.time import Time

from app.data import model
from app.data.repositories import layer2
from app.dataapi.domain import parameterized_query
from app.lib.web import errors
from app.specs import dataapi

DEFAULT = [
    model.RawCatalog.DESIGNATION,
    model.RawCatalog.ICRS,
    model.RawCatalog.REDSHIFT,
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
            [model.RawCatalog.ICRS, model.RawCatalog.DESIGNATION],
        )

    def test_deduplicates(self):
        self.assertEqual(
            parameterized_query.resolve_query_catalogs(
                ["icrs", "icrs"],
                DEFAULT,
            ),
            [model.RawCatalog.ICRS],
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


class QuerySimpleCoordinateConversionTest(unittest.TestCase):
    def setUp(self) -> None:
        self.layer2_repo = mock.Mock()
        self.layer2_repo.query_catalogs.return_value = []
        self.repo = mock.Mock()
        self.manager = parameterized_query.ParameterizedQueryManager(
            layer2_repo=self.layer2_repo,
            repo=self.repo,
            enabled_catalogs=DEFAULT,
            catalog_cfg=mock.Mock(),
            reddening_service=mock.Mock(),
        )

    def _search_params(self) -> layer2.SearchParams:
        return self.layer2_repo.query_catalogs.call_args.args[2]

    def _ordering(self) -> layer2.Ordering | None:
        return self.layer2_repo.query_catalogs.call_args.kwargs.get("ordering")

    def test_coordinate_search_defaults_to_j2000(self):
        ra_fk5, dec_fk5 = 10.0, 20.0
        expected = coords.SkyCoord(
            ra=ra_fk5 * u.Unit("deg"),
            dec=dec_fk5 * u.Unit("deg"),
            frame=coords.FK5(equinox=Time("J2000")),
        ).transform_to("icrs")

        query = dataapi.QuerySimpleRequest(ra=ra_fk5, dec=dec_fk5, radius=0.1)
        with mock.patch("app.dataapi.responders.StructuredResponder") as responder_cls:
            responder_cls.return_value.build_response_from_catalog.return_value = mock.Mock()
            self.manager.query_simple(query)

        got = self._search_params().get_params()
        self.assertAlmostEqual(got["ra"], expected.ra.deg, places=10)
        self.assertAlmostEqual(got["dec"], expected.dec.deg, places=10)
        ordering = self._ordering()
        self.assertIsInstance(ordering, layer2.ICRSDistanceOrdering)
        assert ordering is not None
        self.assertEqual(ordering.get_params(), [expected.ra.deg, expected.dec.deg])

    def test_name_search_has_no_distance_ordering(self):
        query = dataapi.QuerySimpleRequest(name="NGC")
        with mock.patch("app.dataapi.responders.StructuredResponder") as responder_cls:
            responder_cls.return_value.build_response_from_catalog.return_value = mock.Mock()
            self.manager.query_simple(query)

        self.assertIsNone(self._ordering())

    def test_page_is_converted_to_offset(self):
        query = dataapi.QuerySimpleRequest(name="NGC", page=2, page_size=25)
        with mock.patch("app.dataapi.responders.StructuredResponder") as responder_cls:
            responder_cls.return_value.build_response_from_catalog.return_value = mock.Mock()
            self.manager.query_simple(query)

        self.assertEqual(self.layer2_repo.query_catalogs.call_args.args[3], 25)
        self.assertEqual(self.layer2_repo.query_catalogs.call_args.args[4], 50)

    def test_pgc_page_is_converted_to_offset(self):
        query = dataapi.QuerySimpleRequest(pgcs=[1, 2, 3], page=1, page_size=10)
        with mock.patch("app.dataapi.responders.StructuredResponder") as responder_cls:
            responder_cls.return_value.build_response.return_value = mock.Mock()
            self.manager.query_simple(query)

        self.assertEqual(self.repo.query_pgc.call_args.args[2], 10)
        self.assertEqual(self.repo.query_pgc.call_args.args[3], 10)

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
            responder_cls.return_value.build_response_from_catalog.return_value = mock.Mock()
            self.manager.query_simple(query)

        got = self._search_params().get_params()
        self.assertAlmostEqual(got["ra"], ra_j2000, places=5)
        self.assertAlmostEqual(got["dec"], dec_j2000, places=5)

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
            responder_cls.return_value.build_response_from_catalog.return_value = mock.Mock()
            self.manager.query_simple(query)

        got = self._search_params().get_params()
        self.assertAlmostEqual(got["ra"], ra_j2000, places=5)
        self.assertAlmostEqual(got["dec"], dec_j2000, places=5)

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
            responder_cls.return_value.build_response_from_catalog.return_value = mock.Mock()
            self.manager.query_simple(query)

        got = self._search_params().get_params()
        self.assertAlmostEqual(got["ra"], ra_j2000, places=5)
        self.assertAlmostEqual(got["dec"], dec_j2000, places=5)
