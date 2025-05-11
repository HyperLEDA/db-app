import uuid

import structlog

from app.data import model, repositories
from app.domain import homogenization
from app.lib import containers

log: structlog.stdlib.BoundLogger = structlog.get_logger()


def get_homogenization(
    repo: repositories.Layer0Repository,
    metadata: model.Layer0TableMeta,
) -> homogenization.Homogenization:
    db_rules = repo.get_homogenization_rules()
    db_params = repo.get_homogenization_params()

    rules = [new_rule(rule) for rule in db_rules]
    params = [new_params(param) for param in db_params]

    return homogenization.get_homogenization(rules, params, metadata)


def new_rule(rule: model.HomogenizationRule) -> homogenization.Rule:
    return homogenization.Rule(
        model.RawCatalog(rule.catalog),
        rule.parameter,
        homogenization.parse_filters(rule.filters),
        rule.key or "",
        rule.priority or 2**32,
    )


def new_params(params: model.HomogenizationParams) -> homogenization.Params:
    return homogenization.Params(model.RawCatalog(params.catalog), params.key, params.params)


def mark_objects(
    layer0_repo: repositories.Layer0Repository,
    table_id: int,
    batch_size: int,
    cache_enabled: bool = True,
    initial_offset: str | None = "eb047b78-e089-c1e6-16c3-16e9404df520",
) -> None:
    meta = layer0_repo.fetch_metadata(table_id)
    table_stats = layer0_repo.get_table_statistics(table_id)

    h = get_homogenization(layer0_repo, meta)

    # the second condition is needed in case the uploading process was interrupted
    # TODO: in this case the algorithm should determine the last uploaded row and start from there
    if (
        cache_enabled
        and table_stats.total_rows == table_stats.total_original_rows
        and meta.modification_dt is not None
        and table_stats.last_modified_dt is not None
        and meta.modification_dt < table_stats.last_modified_dt
    ):
        log.info("Table was not modified since the last processing", table_id=table_id)
        return

    for offset, data in containers.read_batches(
        layer0_repo.fetch_raw_data,
        lambda d: len(d.data) == 0,
        initial_offset,
        lambda d, _: list(d.data[repositories.INTERNAL_ID_COLUMN_NAME])[-1],
        table_id,
        batch_size=batch_size,
        order_column=repositories.INTERNAL_ID_COLUMN_NAME,
    ):
        objects = h.apply(data.data)
        layer0_repo.upsert_objects(table_id, objects)

        last_uuid = uuid.UUID(list(data.data[repositories.INTERNAL_ID_COLUMN_NAME])[-1])
        max_uuid = uuid.UUID("FFFFFFFF-FFFF-FFFF-FFFF-FFFFFFFFFFFF")

        log.info(
            "Processed batch",
            offset=offset,
            updated_count=len(objects),
            very_approximate_progress=f"{last_uuid.int / max_uuid.int * 100:.02f}%",
        )
