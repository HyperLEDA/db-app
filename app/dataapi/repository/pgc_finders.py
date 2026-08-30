import math

from astropy import units as u

from app.lib import astronomy
from app.lib.storage import postgres

_SPHERE_RADIUS_M = 6371008.7714


def find_pgcs_by_designation(storage: postgres.PgStorage, name: str, limit: int, offset: int) -> list[int]:
    rows = storage.query(
        """
        SELECT DISTINCT pgc
        FROM layer2.designations
        WHERE design ILIKE '%' || %s || '%'
        ORDER BY pgc
        LIMIT %s OFFSET %s
        """,
        params=[name, limit, offset],
    )
    return [int(row["pgc"]) for row in rows]


def find_pgcs_by_equatorial(
    storage: postgres.PgStorage,
    ra: float,
    dec: float,
    radius: u.Quantity,
    limit: int,
    offset: int,
) -> list[int]:
    radius_m = math.radians(astronomy.to(radius, "deg")) * _SPHERE_RADIUS_M
    rows = storage.query(
        """
        SELECT pgc
        FROM layer2.icrs
        WHERE ST_DWithin(
            ST_MakePoint(%s, %s)::geography,
            ST_MakePoint(ra, dec)::geography,
            %s,
            false
        )
        ORDER BY ST_Distance(
            ST_MakePoint(%s, %s)::geography,
            ST_MakePoint(ra, dec)::geography,
            false
        ), pgc
        LIMIT %s OFFSET %s
        """,
        params=[ra, dec, radius_m, ra, dec, limit, offset],
    )
    return [int(row["pgc"]) for row in rows]


def find_pgcs_unfiltered(storage: postgres.PgStorage, limit: int, offset: int) -> list[int]:
    rows = storage.query(
        """
        SELECT id
        FROM common.pgc
        ORDER BY id
        LIMIT %s OFFSET %s
        """,
        params=[limit, offset],
    )
    return [int(row["id"]) for row in rows]
