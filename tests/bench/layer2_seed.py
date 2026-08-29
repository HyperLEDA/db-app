import logging
import os
import statistics
import time
from collections.abc import Callable
from unittest import mock

import structlog
from fastapi import testclient

from app.data import repositories
from app.dataapi import clients, command, domain, presentation
from app.dataapi.repository import Repository
from app.lib.storage import postgres
from tests import lib

N_OBJECTS = int(os.environ.get("BENCH_QUERY_N_OBJECTS", "200000"))

# A dense group so that a 1 arcmin cone returns a full page of results. Coordinates are those of
# M87, matching the query that motivated this benchmark. Its members also share a designation root
# so that the name query returns a full page too, whatever N_OBJECTS is set to.
CLUSTER_CENTER_RA = 187.70591666666667
CLUSTER_CENTER_DEC = 12.39111111111111
CLUSTER_SIZE = 60
CLUSTER_NAME = "IC 1440"

WARMUP_REQUESTS = 3
MEASURED_REQUESTS = 10


def seed_layer2(storage: postgres.PgStorage, n_objects: int) -> None:
    storage.exec(
        "INSERT INTO common.pgc (id) SELECT generate_series(1, %s) ON CONFLICT (id) DO NOTHING",
        params=[n_objects],
    )
    storage.exec(
        """
        INSERT INTO layer2.designation (pgc, design)
        SELECT
            i,
            CASE
                WHEN i <= %s THEN %s || ' ' || i::text
                ELSE CASE i %% 4
                    WHEN 0 THEN 'NGC '
                    WHEN 1 THEN 'IC '
                    WHEN 2 THEN 'UGC '
                    ELSE 'PGC '
                END || i::text
            END
        FROM generate_series(1, %s) AS i
        """,
        params=[CLUSTER_SIZE, CLUSTER_NAME, n_objects],
    )
    # Cluster members sit on a small grid around the centre; everything else is spread over the
    # sphere by a golden-angle sequence in RA and an arcsine transform in declination, so the
    # distribution is uniform in area rather than piling up at the poles.
    storage.exec(
        """
        INSERT INTO layer2.icrs (pgc, ra, e_ra, dec, e_dec)
        SELECT
            i,
            CASE
                WHEN i <= %s
                    THEN %s + (((i - 1) %% 8) - 4) * 0.0015 / cos(radians(%s))
                ELSE ((i::bigint * 137508) %% 360000)::double precision / 1000
            END,
            0.1,
            CASE
                WHEN i <= %s
                    THEN %s + (((i - 1) / 8) - 4) * 0.0015
                ELSE degrees(
                    asin(((i::bigint * 618034) %% 1000000)::double precision / 500000 - 1)
                )
            END,
            0.1
        FROM generate_series(1, %s) AS i
        """,
        params=[
            CLUSTER_SIZE,
            CLUSTER_CENTER_RA,
            CLUSTER_CENTER_DEC,
            CLUSTER_SIZE,
            CLUSTER_CENTER_DEC,
            n_objects,
        ],
    )
    storage.exec(
        """
        INSERT INTO layer2.cz (pgc, cz, e_cz)
        SELECT i, (i %% 30000)::double precision, 1.0
        FROM generate_series(1, %s) AS i
        WHERE i %% 2 = 0
        """,
        params=[n_objects],
    )
    storage.exec(
        """
        INSERT INTO layer2.nature (pgc, type_name)
        SELECT i, CASE i %% 3 WHEN 0 THEN 'G' WHEN 1 THEN 'GC' ELSE 'ClG' END
        FROM generate_series(1, %s) AS i
        """,
        params=[n_objects],
    )

    for table in ("designation", "icrs", "cz", "nature"):
        storage.exec(f"ANALYZE layer2.{table}")


def build_client(storage: postgres.PgStorage) -> tuple[testclient.TestClient, str]:
    logger = structlog.get_logger()
    # Only the catalogs block is taken from the dev config; storage comes from the test container.
    config = command.parse_config("configs/dev/dataapi.yaml")
    actions = domain.Actions(
        layer2_repo=repositories.Layer2Repository(storage, logger),
        repo=Repository(storage),
        catalog_cfg=config.catalogs,
        metadata_repo=repositories.MetadataRepository(storage),
        references_repo=repositories.ReferencesRepository(storage),
        fieldapi_client=mock.create_autospec(clients.FieldAPIClient),
    )
    server = presentation.Server(
        actions,
        config.server,
        logger,
    )

    return testclient.TestClient(server.app), f"{config.server.path_prefix}/v1/query/simple"


def setup_query_simple_bench() -> tuple[lib.TestPostgresStorage, testclient.TestClient, str]:
    structlog.configure(wrapper_class=structlog.make_filtering_bound_logger(logging.WARNING))
    pg_storage = lib.TestPostgresStorage.get()
    storage = pg_storage.get_storage()

    print(f"\nSeeding {N_OBJECTS} layer2 objects...")
    seed_started = time.perf_counter()
    seed_layer2(storage, N_OBJECTS)
    print(f"Seed completed in {time.perf_counter() - seed_started:.2f}s")

    client, url = build_client(storage)
    return pg_storage, client, url


def measure(request: Callable[[], int], label: str) -> float:
    for _ in range(WARMUP_REQUESTS):
        request()

    timings = []
    for _ in range(MEASURED_REQUESTS):
        started = time.perf_counter()
        request()
        timings.append(time.perf_counter() - started)

    timings.sort()
    median = statistics.median(timings)
    print(
        f"{label}: min {timings[0] * 1000:.1f}ms, "
        f"median {median * 1000:.1f}ms, "
        f"p95 {timings[int(len(timings) * 0.95) - 1] * 1000:.1f}ms "
        f"({N_OBJECTS} objects, {MEASURED_REQUESTS} requests)"
    )

    return median
