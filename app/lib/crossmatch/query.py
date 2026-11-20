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

NEIGHBORS_AFTER_ID = f"""
    WITH batch AS (
        SELECT rec.id FROM layer0.records rec
        WHERE rec.table_id = %s AND rec.id > %s ORDER BY rec.id ASC LIMIT %s
    )
    {_NEIGHBOR_BODY}
"""

NEIGHBORS_FOR_IDS = f"""
    WITH batch AS (SELECT rec.id FROM layer0.records rec WHERE rec.id = ANY(%s))
    {_NEIGHBOR_BODY}
"""


def _raw(table_name: str) -> tuple[sql.Composed, sql.Identifier]:
    return sql.SQL("{}.{}").format(sql.Identifier("rawdata"), sql.Identifier(table_name)), sql.Identifier(
        "hyperleda_internal_id"
    )


def neighbors_after_id_filtered(table_name: str, row_filter: sql.Composable) -> sql.Composed:
    raw, id_col = _raw(table_name)
    return sql.SQL(
        """
        WITH batch AS (
            SELECT rec.id FROM layer0.records rec
            JOIN {} raw ON raw.{} = rec.id
            WHERE rec.table_id = %s AND rec.id > %s AND {}
            ORDER BY rec.id ASC LIMIT %s
        )
        """
    ).format(raw, id_col, row_filter) + sql.SQL(_NEIGHBOR_BODY)


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
