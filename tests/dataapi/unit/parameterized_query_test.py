import pytest
from astropy import coordinates as coords
from astropy import units as u
from astropy.time import Time

from app import catalogs
from app.dataapi.domain import parameterized_query
from app.lib import mock
from app.lib.web import errors
from app.specs import dataapi

DEFAULT = [
    catalogs.RawCatalog.DESIGNATION,
    catalogs.RawCatalog.ICRS,
    catalogs.RawCatalog.REDSHIFT,
]


def test_none_returns_default() -> None:
    assert parameterized_query.resolve_query_catalogs(None, DEFAULT) == DEFAULT


def test_subset_preserves_request_order() -> None:
    assert parameterized_query.resolve_query_catalogs(
        ["icrs", "designation"],
        DEFAULT,
    ) == [catalogs.RawCatalog.ICRS, catalogs.RawCatalog.DESIGNATION]


def test_deduplicates() -> None:
    assert parameterized_query.resolve_query_catalogs(
        ["icrs", "icrs"],
        DEFAULT,
    ) == [catalogs.RawCatalog.ICRS]


def test_empty_list_raises() -> None:
    with pytest.raises(errors.RuleValidationError, match="must not be empty"):
        parameterized_query.resolve_query_catalogs([], DEFAULT)


def test_unknown_catalog_raises() -> None:
    with pytest.raises(errors.RuleValidationError, match="Unknown catalog"):
        parameterized_query.resolve_query_catalogs(["not_a_catalog"], DEFAULT)


def test_unavailable_catalog_raises() -> None:
    with pytest.raises(errors.RuleValidationError, match="not available"):
        parameterized_query.resolve_query_catalogs(
            ["note"],
            DEFAULT,
        )


@pytest.fixture
def manager() -> tuple[mock.Mock, parameterized_query.ParameterizedQueryManager]:
    repo = mock.Mock()
    repo.query_catalogs.return_value = []
    repo.find_pgcs_by_designation.return_value = []
    repo.find_pgcs_by_equatorial.return_value = []
    repo.find_pgcs_unfiltered.return_value = []
    return repo, parameterized_query.ParameterizedQueryManager(
        repo=repo,
        enabled_catalogs=DEFAULT,
        catalog_cfg=mock.Mock(),
        reddening_service=mock.Mock(),
    )


def test_coordinate_search_calls_equatorial_finder(
    manager: tuple[mock.Mock, parameterized_query.ParameterizedQueryManager],
) -> None:
    repo, manager_instance = manager
    ra_fk5, dec_fk5 = 10.0, 20.0
    expected = coords.SkyCoord(
        ra=ra_fk5 * u.Unit("deg"),
        dec=dec_fk5 * u.Unit("deg"),
        frame=coords.FK5(equinox=Time("J2000")),
    ).transform_to("icrs")

    query = dataapi.QuerySimpleRequest(ra=ra_fk5, dec=dec_fk5, radius=0.1)
    with mock.patch("app.dataapi.responders.StructuredResponder") as responder_cls:
        responder = mock.MagicMock()
        responder_cls.return_value = responder
        responder.build_response.return_value = mock.Mock()
        manager_instance.query_simple(query)

    repo.find_pgcs_by_equatorial.assert_called_once()
    call = repo.find_pgcs_by_equatorial.call_args
    assert call.args[0] == pytest.approx(expected.ra.deg, abs=1e-10)
    assert call.args[1] == pytest.approx(expected.dec.deg, abs=1e-10)
    assert call.args[3] == query.page_size
    assert call.args[4] == 0


def test_name_search_calls_designation_finder(
    manager: tuple[mock.Mock, parameterized_query.ParameterizedQueryManager],
) -> None:
    repo, manager_instance = manager
    query = dataapi.QuerySimpleRequest(name="NGC", page=2, page_size=25)
    with mock.patch("app.dataapi.responders.StructuredResponder") as responder_cls:
        responder = mock.MagicMock()
        responder_cls.return_value = responder
        responder.build_response.return_value = mock.Mock()
        manager_instance.query_simple(query)

    repo.find_pgcs_by_designation.assert_called_once_with("NGC", 25, 50)


def test_pgc_filter_paginates_in_memory(
    manager: tuple[mock.Mock, parameterized_query.ParameterizedQueryManager],
) -> None:
    repo, manager_instance = manager
    query = dataapi.QuerySimpleRequest(pgcs=[3, 1, 2], page=1, page_size=1)
    with mock.patch("app.dataapi.responders.StructuredResponder") as responder_cls:
        responder = mock.MagicMock()
        responder_cls.return_value = responder
        responder.build_response.return_value = mock.Mock()
        manager_instance.query_simple(query)

    repo.find_pgcs_by_designation.assert_not_called()
    repo.find_pgcs_by_equatorial.assert_not_called()
    repo.query_catalogs.assert_called_once()
    assert repo.query_catalogs.call_args.args[1] == [2]


def test_coordinate_search_precesses_b1950(
    manager: tuple[mock.Mock, parameterized_query.ParameterizedQueryManager],
) -> None:
    repo, manager_instance = manager
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
        responder = mock.MagicMock()
        responder_cls.return_value = responder
        responder.build_response.return_value = mock.Mock()
        manager_instance.query_simple(query)

    call = repo.find_pgcs_by_equatorial.call_args
    assert call.args[0] == pytest.approx(ra_j2000, abs=1e-5)
    assert call.args[1] == pytest.approx(dec_j2000, abs=1e-5)


def test_galactic_coordinate_search_converts_to_icrs(
    manager: tuple[mock.Mock, parameterized_query.ParameterizedQueryManager],
) -> None:
    repo, manager_instance = manager
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
        responder = mock.MagicMock()
        responder_cls.return_value = responder
        responder.build_response.return_value = mock.Mock()
        manager_instance.query_simple(query)

    call = repo.find_pgcs_by_equatorial.call_args
    assert call.args[0] == pytest.approx(ra_j2000, abs=1e-5)
    assert call.args[1] == pytest.approx(dec_j2000, abs=1e-5)


def test_supergalactic_coordinate_search_converts_to_icrs(
    manager: tuple[mock.Mock, parameterized_query.ParameterizedQueryManager],
) -> None:
    repo, manager_instance = manager
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
        responder = mock.MagicMock()
        responder_cls.return_value = responder
        responder.build_response.return_value = mock.Mock()
        manager_instance.query_simple(query)

    call = repo.find_pgcs_by_equatorial.call_args
    assert call.args[0] == pytest.approx(ra_j2000, abs=1e-5)
    assert call.args[1] == pytest.approx(dec_j2000, abs=1e-5)


def test_unfiltered_search_calls_unfiltered_finder(
    manager: tuple[mock.Mock, parameterized_query.ParameterizedQueryManager],
) -> None:
    repo, manager_instance = manager
    query = dataapi.QuerySimpleRequest(page=1, page_size=10)
    with mock.patch("app.dataapi.responders.StructuredResponder") as responder_cls:
        responder = mock.MagicMock()
        responder_cls.return_value = responder
        responder.build_response.return_value = mock.Mock()
        manager_instance.query_simple(query)

    repo.find_pgcs_unfiltered.assert_called_once_with(10, 10)


def test_always_builds_response(
    manager: tuple[mock.Mock, parameterized_query.ParameterizedQueryManager],
) -> None:
    _, manager_instance = manager
    query = dataapi.QuerySimpleRequest(name="NGC")
    with mock.patch("app.dataapi.responders.StructuredResponder") as responder_cls:
        responder = mock.MagicMock()
        responder_cls.return_value = responder
        responder.build_response.return_value = mock.Mock()
        manager_instance.query_simple(query)

    responder.build_response.assert_called_once()
    responder.build_response_from_catalog.assert_not_called()
