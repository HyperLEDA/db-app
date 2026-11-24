from psycopg import sql

# Below this many records, index lookups per record are cheaper than hash joins over whole tables.
BULK_THRESHOLD = 20_000

_ZONE_HEIGHT = "(%(radius)s * 2.002)"
_ZONE_MIN = f"(floor(-90 / {_ZONE_HEIGHT})::int - 1)"
_ZONE_EDGE = f"(greatest(abs(zone), abs(zone + 1)) * {_ZONE_HEIGHT} + {_ZONE_HEIGHT})"
_PROBE_ZONE = f"(floor(p.dec / {_ZONE_HEIGHT} - 0.5)::int + dz.dz)"
_PROBE_CELLS = f"((SELECT cells FROM zone_cells)[{_PROBE_ZONE} - {_ZONE_MIN} + 1])"
_CATALOG_ZONE = f"floor(l2.dec / {_ZONE_HEIGHT})::int"
_CATALOG_CELLS = f"((SELECT cells FROM zone_cells)[{_CATALOG_ZONE} - {_ZONE_MIN} + 1])"

_INDEX_NEIGHBORS = """
    neighbors AS (
        SELECT
            p.n,
            array_agg(l2.pgc) AS pgcs, array_agg(l2.ra) AS ras, array_agg(l2.dec) AS decs,
            array_agg(l2.name) AS designs, array_agg(l2.objtype) AS types,
            array_agg({neighbor_cz}) AS czs
        FROM points p
        JOIN layer2.objects l2
            ON l2.ra IS NOT NULL AND l2.dec IS NOT NULL
            AND ST_DWithin(
                ST_MakePoint(p.ra, p.dec)::geography, ST_MakePoint(l2.ra, l2.dec)::geography,
                RADIANS(%(radius)s) * 6371008.7714, false)
        GROUP BY p.n
    )
"""

# Zones algorithm (Gray et al., "The Zones Algorithm for Finding Points-Near-a-Point"): the sky is cut into declination
# zones at least two radii high and each zone into RA cells at least as wide as a search circle anywhere in or next to
# the zone, so every neighbor of a point lies in the 2x2 cells nearest to it. The equality join on (zone, cell) runs
# over sequential scans; ST_DWithin stays the exact predicate.
# Cell counts per zone are looked up in an array rather than joined: the planner cannot estimate a join against a
# generated zone list and falls back to per-probe GiST lookups.
_ZONE_NEIGHBORS = f"""
    zone_cells AS MATERIALIZED (
        SELECT array_agg(
            CASE WHEN {_ZONE_EDGE} >= 90 OR sin(radians(%(radius)s)) >= cos(radians({_ZONE_EDGE})) THEN 1
            ELSE greatest(1, floor(
                360 / (2.002 * degrees(asin(sin(radians(%(radius)s)) / cos(radians({_ZONE_EDGE})))))
            ))::int
            END
            ORDER BY zone
        ) AS cells
        FROM generate_series({_ZONE_MIN}, floor(90 / {_ZONE_HEIGHT})::int + 1) AS zone
    ),
    probes AS MATERIALIZED (
        SELECT
            z.n, z.ra, z.dec, z.zone,
            ((floor(z.ra * z.cells / 360 - 0.5)::int + k.k) %% z.cells + z.cells) %% z.cells AS cell
        FROM (
            SELECT p.n, p.ra, p.dec, {_PROBE_ZONE} AS zone, {_PROBE_CELLS} AS cells
            FROM points p CROSS JOIN (VALUES (0), (1)) AS dz(dz)
        ) z
        CROSS JOIN (VALUES (0), (1)) AS k(k)
        WHERE k.k < z.cells
    ),
    catalog AS (
        SELECT
            l2.pgc, l2.ra, l2.dec, l2.name, l2.objtype, {_CATALOG_ZONE} AS zone,
            floor(l2.ra * {_CATALOG_CELLS} / 360)::int %% {_CATALOG_CELLS} AS cell
        FROM layer2.objects l2
        WHERE l2.ra IS NOT NULL AND l2.dec IS NOT NULL
    ),
    neighbors AS (
        SELECT
            pr.n,
            array_agg(l2.pgc) AS pgcs, array_agg(l2.ra) AS ras, array_agg(l2.dec) AS decs,
            array_agg(l2.name) AS designs, array_agg(l2.objtype) AS types, array_agg({{neighbor_cz}}) AS czs
        FROM probes pr
        JOIN catalog l2 ON l2.zone = pr.zone AND l2.cell = pr.cell
        {{neighbor_cz_join}}
        WHERE l2.dec BETWEEN pr.dec - %(radius)s * 1.001 AND pr.dec + %(radius)s * 1.001
          AND ST_DWithin(
              ST_MakePoint(pr.ra, pr.dec)::geography, ST_MakePoint(l2.ra, l2.dec)::geography,
              RADIANS(%(radius)s) * 6371008.7714, false)
        GROUP BY pr.n
    )
"""

_INPUT = """
    WITH rec AS (
        {records}
    ),
    named AS (
        SELECT d.record_id, d.design FROM rec JOIN designation.data d ON d.record_id = rec.id
    ),
    same_name AS (
        SELECT x.design, array_agg(x.pgc) AS pgcs
        FROM (
            SELECT d.design, r.pgc
            FROM designation.data d JOIN layer0.records r ON r.id = d.record_id
            WHERE r.pgc IS NOT NULL AND d.design IN (SELECT design FROM named)
            UNION ALL
            SELECT l2.name, l2.pgc FROM layer2.objects l2 WHERE l2.name IN (SELECT design FROM named)
        ) x
        GROUP BY x.design
    ),
    points AS MATERIALIZED (
        SELECT row_number() OVER ()::int AS n, rec.id, nc.ra, nc.dec
        FROM rec JOIN icrs.data nc ON nc.record_id = rec.id
    ),
    {neighbors}
    SELECT
        rec.id, rec.claimed_pgc, points.ra, points.dec, named.design, {cz} AS cz, {type_name} AS type_name,
        same_name.pgcs AS same_name_pgcs,
        nb.pgcs AS neighbor_pgcs, nb.ras AS neighbor_ras, nb.decs AS neighbor_decs,
        nb.designs AS neighbor_designs, nb.types AS neighbor_types, nb.czs AS neighbor_czs
    FROM rec
    LEFT JOIN points ON points.id = rec.id
    LEFT JOIN named ON named.record_id = rec.id
    {cz_join}
    {type_join}
    LEFT JOIN same_name ON same_name.design = named.design
    LEFT JOIN neighbors nb ON nb.n = points.n
"""


def _raw(table_name: str) -> tuple[sql.Composed, sql.Identifier]:
    return sql.SQL("{}.{}").format(sql.Identifier("rawdata"), sql.Identifier(table_name)), sql.Identifier(
        "hyperleda_internal_id"
    )


def _claimed(pgc_column: str | None) -> sql.Composable:
    return sql.SQL("raw.{}").format(sql.Identifier(pgc_column)) if pgc_column else sql.SQL("NULL::integer")


def table_records(table_name: str, row_filter: sql.Composable | None, pgc_column: str | None) -> sql.Composed:
    raw, id_col = _raw(table_name)
    needs_raw = row_filter is not None or pgc_column is not None
    return sql.SQL(
        "SELECT r.id, {claimed} AS claimed_pgc FROM layer0.records r {raw_join} "
        "WHERE r.table_id = %(table_id)s AND r.pgc IS NULL AND {row_filter}"
    ).format(
        claimed=_claimed(pgc_column),
        raw_join=sql.SQL("JOIN {} raw ON raw.{} = r.id").format(raw, id_col) if needs_raw else sql.SQL(""),
        row_filter=row_filter if row_filter is not None else sql.SQL("true"),
    )


def id_records(table_name: str, pgc_column: str | None) -> sql.Composed:
    raw, id_col = _raw(table_name)
    return sql.SQL("SELECT r.id, {claimed} AS claimed_pgc FROM unnest(%(ids)s::text[]) AS r(id) {raw_join}").format(
        claimed=_claimed(pgc_column),
        raw_join=sql.SQL("JOIN {} raw ON raw.{} = r.id").format(raw, id_col) if pgc_column else sql.SQL(""),
    )


def crossmatch_input(
    records: sql.Composable, *, include_redshift: bool, include_nature: bool, bulk: bool
) -> sql.Composed:
    neighbor_cz, neighbor_cz_join = "NULL::double precision", ""
    if include_redshift and bulk:
        neighbor_cz, neighbor_cz_join = "l2_cz.cz", "LEFT JOIN layer2.cz l2_cz ON l2_cz.pgc = l2.pgc"
    elif include_redshift:
        # A scalar subquery: the ST_DWithin row estimate is far too high and a join yields a seq scan of layer2.cz.
        neighbor_cz = "(SELECT l2_cz.cz FROM layer2.cz l2_cz WHERE l2_cz.pgc = l2.pgc)"
    return sql.SQL(_INPUT).format(
        records=records,
        neighbors=sql.SQL(_ZONE_NEIGHBORS if bulk else _INDEX_NEIGHBORS).format(
            neighbor_cz=sql.SQL(neighbor_cz), neighbor_cz_join=sql.SQL(neighbor_cz_join)
        ),
        cz=sql.SQL("z.cz" if include_redshift else "NULL::double precision"),
        cz_join=sql.SQL("LEFT JOIN cz.data z ON z.record_id = rec.id" if include_redshift else ""),
        type_name=sql.SQL("n.type_name" if include_nature else "NULL::text"),
        type_join=sql.SQL("LEFT JOIN nature.data n ON n.record_id = rec.id" if include_nature else ""),
    )


def filtered_record_count(table_name: str, row_filter: sql.Composable) -> sql.Composed:
    raw, id_col = _raw(table_name)
    return sql.SQL(
        "SELECT COUNT(*) AS cnt FROM layer0.records rec JOIN {} raw ON raw.{} = rec.id WHERE rec.table_id = %s AND {}"
    ).format(raw, id_col, row_filter)


def filtered_record_sample(table_name: str, row_filter: sql.Composable) -> sql.Composed:
    raw, id_col = _raw(table_name)
    return sql.SQL(
        """
        SELECT rec.id FROM layer0.records rec JOIN {} raw ON raw.{} = rec.id
        WHERE rec.table_id = %s AND {} ORDER BY random() LIMIT %s
        """
    ).format(raw, id_col, row_filter)


def filtered_tablesample(table_name: str, row_filter: sql.Composable) -> sql.Composed:
    raw, id_col = _raw(table_name)
    return sql.SQL(
        """
        WITH s AS MATERIALIZED (
            SELECT raw.{} AS id, COALESCE(({}), false) AS passes FROM {} raw TABLESAMPLE SYSTEM (%s)
        )
        SELECT
            (SELECT COUNT(*) FROM s) AS scanned,
            (SELECT COUNT(*) FROM s WHERE passes) AS passing,
            ARRAY(SELECT id FROM s WHERE passes ORDER BY random() LIMIT %s) AS ids
        """
    ).format(id_col, row_filter, raw)
