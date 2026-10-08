import pytest
import structlog
from astropy import units as u

from app import catalogs
from app.dataapi import model, repository
from app.lib.storage import postgres
from tests.lib import layer_seed
from tests.lib.postgres import PostgresTestStorage

pytestmark = pytest.mark.usefixtures("cleared_pg_storage")


@pytest.fixture(scope="module")
def repo(pg_storage: PostgresTestStorage) -> repository.Repository:
    return repository.Repository(pg_storage.get_storage(), structlog.get_logger())


@pytest.fixture(scope="module")
def storage(pg_storage: PostgresTestStorage) -> postgres.PgStorage:
    return pg_storage.get_storage()


def _save_layer2_data(storage: postgres.PgStorage, objects: list[catalogs.layer2.Layer2Object]) -> None:
    by_table: dict[str, list[tuple[int, catalogs.layer2.CatalogObject]]] = {}
    for obj in objects:
        for catalog_obj in obj.data:
            layer2_table = catalog_obj.table()
            if layer2_table not in by_table:
                by_table[layer2_table] = []
            by_table[layer2_table].append((obj.pgc, catalog_obj))
    for table_name, table_entries in by_table.items():
        if not table_entries:
            continue
        columns = table_entries[0][1].keys()
        all_columns = ["pgc", *columns]
        placeholders = ", ".join(["%s"] * len(all_columns))
        update_set = ", ".join(f"{col} = EXCLUDED.{col}" for col in all_columns)
        query = (
            f"INSERT INTO {table_name} ({', '.join(all_columns)}) "
            f"VALUES ({placeholders}) ON CONFLICT (pgc) DO UPDATE SET {update_set}"
        )
        rows = [[pgc, *[catalog_obj.to_row()[col] for col in columns]] for pgc, catalog_obj in table_entries]
        storage.execute_batch(query, rows)


def _get_table(storage: postgres.PgStorage, table_name: str) -> int:
    bib_id = layer_seed.create_bibliography(storage, "123456", 2000, ["test"], "test")
    return layer_seed.create_table(storage, table_name, bib_id)


def test_one_object(
    repo: repository.Repository,
    storage: postgres.PgStorage,
) -> None:
    objects: list[catalogs.layer2.Layer2Object] = [
        catalogs.layer2.Layer2Object(1, [catalogs.layer2.DesignationCatalogObject(design="test")]),
        catalogs.layer2.Layer2Object(2, [catalogs.layer2.DesignationCatalogObject(design="test2")]),
    ]

    layer_seed.register_pgcs(storage, [1, 2])
    _save_layer2_data(storage, objects)

    actual = repo.query_catalogs([catalogs.layer2.Catalog.DESIGNATION], [1])

    assert len(actual) == 1
    assert actual[0].pgc == 1
    assert actual[0].catalogs.designation is not None
    assert actual[0].catalogs.designation.name == "test"


def test_find_pgcs_by_designation(
    repo: repository.Repository,
    storage: postgres.PgStorage,
) -> None:
    _get_table(storage, "desig_table")
    layer_seed.register_records(storage, "desig_table", ["r1", "r2", "r3"])
    layer_seed.register_pgcs(storage, [10, 20, 30])
    layer_seed.upsert_pgc(storage, {"r1": 10, "r2": 20, "r3": 30})
    layer_seed.save_structured_data(
        storage,
        "designation.data",
        ["design"],
        ["r1", "r2", "r3"],
        [["IC 1440"], ["NGC 500"], ["IC 999"]],
        conflict_keys=catalogs.layer1.DesignationCatalogObject.layer1_primary_keys(),
    )

    assert repo.find_pgcs_by_designation("IC 144", 10, 0) == []
    assert repo.find_pgcs_by_designation("IC 1440", 10, 0) == [10]
    assert repo.find_pgcs_by_designation("IC 144%", 10, 0) == [10]


def test_find_pgcs_by_designation_ranks_by_match_closeness(
    repo: repository.Repository,
    storage: postgres.PgStorage,
) -> None:
    _get_table(storage, "desig_table")
    record_ids = ["r1", "r2", "r3", "r4", "r5"]
    layer_seed.register_records(storage, "desig_table", record_ids)
    layer_seed.register_pgcs(storage, [10, 20, 30, 40, 50])
    layer_seed.upsert_pgc(
        storage,
        {"r1": 10, "r2": 20, "r3": 30, "r4": 40, "r5": 50},
    )
    layer_seed.save_structured_data(
        storage,
        "designation.data",
        ["design"],
        record_ids,
        [
            ["IC 144ABC"],
            ["XIC 144"],
            ["IC 144"],
            ["IC 144A"],
            ["FOO IC 144"],
        ],
        conflict_keys=catalogs.layer1.DesignationCatalogObject.layer1_primary_keys(),
    )

    assert repo.find_pgcs_by_designation("IC 144", 10, 0) == [30]
    assert repo.find_pgcs_by_designation("IC 144%", 10, 0) == [30, 40, 10]
    assert repo.find_pgcs_by_designation("IC 144_", 10, 0) == [40]
    assert repo.find_pgcs_by_designation("IC 144%", 1, 0) == [30]
    assert repo.find_pgcs_by_designation("IC 144%", 1, 1) == [40]
    assert repo.find_pgcs_by_designation("IC 144%", 1, 2) == [10]


def test_find_pgcs_by_designation_exact_deduplicates_and_paginates(
    repo: repository.Repository,
    storage: postgres.PgStorage,
) -> None:
    _get_table(storage, "desig_exact")
    layer_seed.register_records(storage, "desig_exact", ["r1", "r2", "r3", "r4", "unassigned"])
    layer_seed.register_pgcs(storage, [30, 10, 20])
    layer_seed.upsert_pgc(storage, {"r1": 30, "r2": 10, "r3": 20, "r4": 10})
    layer_seed.save_structured_data(
        storage,
        "designation.data",
        ["design"],
        ["r1", "r2", "r3", "r4", "unassigned"],
        [["M 31"], ["M 31"], ["M 31"], ["M 31"], ["M 31"]],
        conflict_keys=catalogs.layer1.DesignationCatalogObject.layer1_primary_keys(),
    )

    assert repo.find_pgcs_by_designation("M 31", 2, 0) == [10, 20]
    assert repo.find_pgcs_by_designation("M 31", 2, 2) == [30]
    assert repo.find_pgcs_by_designation("M 32", 10, 0) == []


def test_several_objects(
    repo: repository.Repository,
    storage: postgres.PgStorage,
) -> None:
    objects: list[catalogs.layer2.Layer2Object] = [
        catalogs.layer2.Layer2Object(1, [catalogs.layer2.ICRSCatalogObject(ra=10, dec=10, e_ra=0.1, e_dec=0.1)]),
        catalogs.layer2.Layer2Object(2, [catalogs.layer2.ICRSCatalogObject(ra=11, dec=11, e_ra=0.1, e_dec=0.1)]),
    ]

    layer_seed.register_pgcs(storage, [1, 2])
    _save_layer2_data(storage, objects)

    pgcs = repo.find_pgcs_by_equatorial(12, 12, 10 * u.Unit("deg"), 10, 0)
    actual = repo.query_catalogs([catalogs.layer2.Catalog.ICRS], pgcs)

    assert [obj.pgc for obj in actual] == [2, 1]
    assert actual[0].catalogs.icrs is not None
    assert actual[0].catalogs.icrs.ra == pytest.approx(11)


def test_several_catalogs(
    repo: repository.Repository,
    storage: postgres.PgStorage,
) -> None:
    objects = [
        catalogs.layer2.Layer2Object(1, [catalogs.layer2.ICRSCatalogObject(ra=10, dec=10, e_ra=0.1, e_dec=0.1)]),
        catalogs.layer2.Layer2Object(
            2,
            [
                catalogs.layer2.ICRSCatalogObject(ra=11, dec=11, e_ra=0.1, e_dec=0.1),
                catalogs.layer2.DesignationCatalogObject(design="test2"),
            ],
        ),
    ]

    layer_seed.register_pgcs(storage, [1, 2])
    _save_layer2_data(storage, objects)

    actual = repo.query_catalogs(
        [catalogs.layer2.Catalog.ICRS, catalogs.layer2.Catalog.DESIGNATION],
        [2],
    )

    assert len(actual) == 1
    assert actual[0].pgc == 2
    assert actual[0].catalogs.icrs is not None
    assert actual[0].catalogs.designation is not None
    assert actual[0].catalogs.designation.name == "test2"


def test_pagination(
    repo: repository.Repository,
    storage: postgres.PgStorage,
) -> None:
    objects: list[catalogs.layer2.Layer2Object] = [
        catalogs.layer2.Layer2Object(1, [catalogs.layer2.ICRSCatalogObject(ra=10, dec=10, e_ra=0.1, e_dec=0.1)]),
        catalogs.layer2.Layer2Object(2, [catalogs.layer2.ICRSCatalogObject(ra=11, dec=11, e_ra=0.1, e_dec=0.1)]),
        catalogs.layer2.Layer2Object(3, [catalogs.layer2.ICRSCatalogObject(ra=12, dec=12, e_ra=0.1, e_dec=0.1)]),
        catalogs.layer2.Layer2Object(4, [catalogs.layer2.ICRSCatalogObject(ra=13, dec=13, e_ra=0.1, e_dec=0.1)]),
        catalogs.layer2.Layer2Object(5, [catalogs.layer2.ICRSCatalogObject(ra=14, dec=14, e_ra=0.1, e_dec=0.1)]),
    ]

    layer_seed.register_pgcs(storage, [1, 2, 3, 4, 5])
    _save_layer2_data(storage, objects)

    pgcs = repo.find_pgcs_by_equatorial(12, 12, 10 * u.Unit("deg"), 2, 1)
    actual = repo.query_catalogs([catalogs.layer2.Catalog.ICRS], pgcs)

    assert len(actual) == 2


def _query_icrs_in_radius(
    repo: repository.Repository,
    ra: float,
    dec: float,
    radius: float,
    raw_catalogs: list[catalogs.layer2.Catalog] | None = None,
) -> list[model.Layer2Object]:
    pgcs = repo.find_pgcs_by_equatorial(ra, dec, radius * u.Unit("deg"), 10, 0)
    return repo.query_catalogs(raw_catalogs or [catalogs.layer2.Catalog.ICRS], pgcs)


def test_cone_search_wraps_around_ra_zero(
    repo: repository.Repository,
    storage: postgres.PgStorage,
) -> None:
    objects: list[catalogs.layer2.Layer2Object] = [
        catalogs.layer2.Layer2Object(1, [catalogs.layer2.ICRSCatalogObject(ra=359.99, dec=0, e_ra=0.1, e_dec=0.1)]),
        catalogs.layer2.Layer2Object(2, [catalogs.layer2.ICRSCatalogObject(ra=0.01, dec=0, e_ra=0.1, e_dec=0.1)]),
        catalogs.layer2.Layer2Object(3, [catalogs.layer2.ICRSCatalogObject(ra=180, dec=0, e_ra=0.1, e_dec=0.1)]),
    ]

    layer_seed.register_pgcs(storage, [1, 2, 3])
    _save_layer2_data(storage, objects)

    actual = _query_icrs_in_radius(repo, ra=0.0, dec=0.0, radius=0.05)

    assert {obj.pgc for obj in actual} == {1, 2}


def test_cone_search_accounts_for_declination_convergence(
    repo: repository.Repository,
    storage: postgres.PgStorage,
) -> None:
    objects: list[catalogs.layer2.Layer2Object] = [
        catalogs.layer2.Layer2Object(1, [catalogs.layer2.ICRSCatalogObject(ra=100, dec=80, e_ra=0.1, e_dec=0.1)]),
        catalogs.layer2.Layer2Object(2, [catalogs.layer2.ICRSCatalogObject(ra=102, dec=80, e_ra=0.1, e_dec=0.1)]),
        catalogs.layer2.Layer2Object(3, [catalogs.layer2.ICRSCatalogObject(ra=100, dec=79, e_ra=0.1, e_dec=0.1)]),
    ]

    layer_seed.register_pgcs(storage, [1, 2, 3])
    _save_layer2_data(storage, objects)

    actual = _query_icrs_in_radius(repo, ra=100.0, dec=80.0, radius=0.5)

    assert {obj.pgc for obj in actual} == {1, 2}


def test_distance_ordering_sorts_by_true_angular_separation(
    repo: repository.Repository,
    storage: postgres.PgStorage,
) -> None:
    objects: list[catalogs.layer2.Layer2Object] = [
        catalogs.layer2.Layer2Object(1, [catalogs.layer2.ICRSCatalogObject(ra=14, dec=60, e_ra=0.1, e_dec=0.1)]),
        catalogs.layer2.Layer2Object(2, [catalogs.layer2.ICRSCatalogObject(ra=10, dec=62.5, e_ra=0.1, e_dec=0.1)]),
    ]

    layer_seed.register_pgcs(storage, [1, 2])
    _save_layer2_data(storage, objects)

    actual = _query_icrs_in_radius(repo, ra=10.0, dec=60.0, radius=5.0)

    assert [obj.pgc for obj in actual] == [1, 2]


def test_coordinate_filter_when_icrs_catalog_not_requested(
    repo: repository.Repository,
    storage: postgres.PgStorage,
) -> None:
    objects = [
        catalogs.layer2.Layer2Object(
            1,
            [
                catalogs.layer2.ICRSCatalogObject(ra=10, dec=10, e_ra=0.1, e_dec=0.1),
                catalogs.layer2.RedshiftCatalogObject(cz=100, e_cz=1),
            ],
        ),
    ]

    layer_seed.register_pgcs(storage, [1])
    _save_layer2_data(storage, objects)

    actual = _query_icrs_in_radius(
        repo,
        ra=10.0,
        dec=10.0,
        radius=1.0,
        raw_catalogs=[catalogs.layer2.Catalog.REDSHIFT],
    )

    assert len(actual) == 1
    assert actual[0].pgc == 1
    assert actual[0].catalogs.redshift is not None
    assert actual[0].catalogs.redshift.cz == pytest.approx(100)


def test_query_by_pgc_list(
    repo: repository.Repository,
    storage: postgres.PgStorage,
) -> None:
    objects = [
        catalogs.layer2.Layer2Object(
            1,
            [
                catalogs.layer2.DesignationCatalogObject(design="test"),
                catalogs.layer2.RedshiftCatalogObject(cz=100, e_cz=1),
            ],
        ),
    ]

    layer_seed.register_pgcs(storage, [1])
    _save_layer2_data(storage, objects)

    actual = repo.query_catalogs([catalogs.layer2.Catalog.REDSHIFT], [1])

    assert len(actual) == 1
    assert actual[0].catalogs.redshift is not None


def test_query_photometry_total(
    repo: repository.Repository,
    storage: postgres.PgStorage,
) -> None:
    _get_table(storage, "phot_table")
    layer_seed.register_records(storage, "phot_table", ["r1"])
    layer_seed.register_pgcs(storage, [5001])
    layer_seed.upsert_pgc(storage, {"r1": 5001})
    layer_seed.save_structured_data(
        storage,
        catalogs.layer1.PhotometryTotalCatalogObject.layer1_table(),
        ["band", "mag", "e_mag", "method"],
        ["r1"],
        [["V", 12.5, 0.1, "psf"]],
        conflict_keys=catalogs.layer1.PhotometryTotalCatalogObject.layer1_primary_keys(),
    )

    result = repo.query_catalogs([catalogs.layer2.Catalog.PHOTOMETRY__TOTAL], [5001])

    assert len(result) == 1
    photometry = result[0].catalogs.photometry_total
    assert photometry is not None
    assert len(photometry.measurements) == 1
    measurement = photometry.measurements[0]
    assert measurement.band == "V"
    assert measurement.magsys == "Vega"
    assert measurement.method == "psf"
    assert measurement.photsys == "UBVRIJHKL"
    assert measurement.filter == "V"
    assert measurement.wavelength == pytest.approx(5501.40)
    assert measurement.mag == pytest.approx(12.5)
    assert measurement.e_mag is not None
    assert measurement.e_mag == pytest.approx(0.1)


def test_preserves_pgc_order_from_input(
    repo: repository.Repository,
    storage: postgres.PgStorage,
) -> None:
    objects: list[catalogs.layer2.Layer2Object] = [
        catalogs.layer2.Layer2Object(1, [catalogs.layer2.DesignationCatalogObject(design="a")]),
        catalogs.layer2.Layer2Object(2, [catalogs.layer2.DesignationCatalogObject(design="b")]),
        catalogs.layer2.Layer2Object(3, [catalogs.layer2.DesignationCatalogObject(design="c")]),
    ]

    layer_seed.register_pgcs(storage, [1, 2, 3])
    _save_layer2_data(storage, objects)

    actual = repo.query_catalogs([catalogs.layer2.Catalog.DESIGNATION], [3, 1, 2])

    assert [obj.pgc for obj in actual] == [3, 1, 2]
