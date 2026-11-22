from psycopg import sql

_NEIGHBOR_BODY = """
    SELECT
        b.id AS new_id, nc.ra AS new_ra, nc.dec AS new_dec, new_desig.design AS new_design,
        new_cz.cz AS new_cz, rec_nat.type_name AS new_type, l2.pgc AS existing_pgc,
        l2.ra AS existing_ra, l2.dec AS existing_dec, l2.name AS existing_design,
        l2_cz.cz AS existing_cz, l2.objtype AS existing_type
    FROM batch b
    LEFT JOIN icrs.data nc ON b.id = nc.record_id
    LEFT JOIN designation.data new_desig ON b.id = new_desig.record_id
    LEFT JOIN cz.data new_cz ON b.id = new_cz.record_id
    LEFT JOIN nature.data rec_nat ON b.id = rec_nat.record_id
    LEFT JOIN LATERAL (
        SELECT l2.* FROM layer2.objects l2
        WHERE nc.record_id IS NOT NULL AND l2.ra IS NOT NULL AND l2.dec IS NOT NULL
          AND ST_DWithin(
              ST_MakePoint(nc.ra, nc.dec)::geography, ST_MakePoint(l2.ra, l2.dec)::geography,
              RADIANS(%s) * 6371008.7714, false)
    ) l2 ON true
    LEFT JOIN layer2.cz l2_cz ON l2.pgc = l2_cz.pgc
    ORDER BY b.id ASC
"""

NEIGHBORS_FOR_IDS = f"""
    WITH batch AS (SELECT id FROM unnest(%s::text[]) AS ids(id))
    {_NEIGHBOR_BODY}
"""

NEIGHBORS_FOR_COORDS = """
    SELECT
        b.id AS new_id, l2.pgc AS existing_pgc, l2.ra AS existing_ra, l2.dec AS existing_dec,
        l2.name AS existing_design, l2.objtype AS existing_type,
        -- scalar subquery: the ST_DWithin row estimate is far too high and otherwise yields a seq scan of layer2.cz
        (SELECT l2_cz.cz FROM layer2.cz l2_cz WHERE l2_cz.pgc = l2.pgc) AS existing_cz
    FROM unnest(%s::text[], %s::double precision[], %s::double precision[]) AS b(id, ra, dec)
    JOIN layer2.objects l2
        ON l2.ra IS NOT NULL AND l2.dec IS NOT NULL
        AND ST_DWithin(
            ST_MakePoint(b.ra, b.dec)::geography, ST_MakePoint(l2.ra, l2.dec)::geography,
            RADIANS(%s) * 6371008.7714, false)
"""


def _raw(table_name: str) -> tuple[sql.Composed, sql.Identifier]:
    return sql.SQL("{}.{}").format(sql.Identifier("rawdata"), sql.Identifier(table_name)), sql.Identifier(
        "hyperleda_internal_id"
    )


def table_input(table_name: str, row_filter: sql.Composable | None, pgc_column: str | None) -> sql.Composed:
    raw, id_col = _raw(table_name)
    needs_raw = row_filter is not None or pgc_column is not None
    return sql.SQL(
        """
        WITH rec AS (
            SELECT r.id, {claimed} AS claimed_pgc
            FROM layer0.records r {raw_join}
            WHERE r.table_id = %s AND {row_filter}
        ),
        named AS (
            SELECT d.record_id, d.design FROM rec JOIN designation.data d ON d.record_id = rec.id
        ),
        same_name AS (
            SELECT x.design, array_agg(DISTINCT x.pgc ORDER BY x.pgc) AS pgcs
            FROM (
                SELECT d.design, r.pgc
                FROM designation.data d JOIN layer0.records r ON r.id = d.record_id
                WHERE r.pgc IS NOT NULL AND d.design IN (SELECT design FROM named)
                UNION ALL
                SELECT l2.name, l2.pgc FROM layer2.objects l2 WHERE l2.name IN (SELECT design FROM named)
            ) x
            GROUP BY x.design
        )
        SELECT
            rec.id, rec.claimed_pgc, nc.ra, nc.dec, named.design, z.cz, n.type_name,
            same_name.pgcs AS same_name_pgcs
        FROM rec
        LEFT JOIN icrs.data nc ON nc.record_id = rec.id
        LEFT JOIN named ON named.record_id = rec.id
        LEFT JOIN cz.data z ON z.record_id = rec.id
        LEFT JOIN nature.data n ON n.record_id = rec.id
        LEFT JOIN same_name ON same_name.design = named.design
        """
    ).format(
        claimed=sql.SQL("raw.{}").format(sql.Identifier(pgc_column)) if pgc_column else sql.SQL("NULL::integer"),
        raw_join=sql.SQL("JOIN {} raw ON raw.{} = r.id").format(raw, id_col) if needs_raw else sql.SQL(""),
        row_filter=row_filter if row_filter is not None else sql.SQL("true"),
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
