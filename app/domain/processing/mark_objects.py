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
        lambda data: len(data.data) == 0,
        table_id,
        batch_size=batch_size,
    ):
        objects = h.apply(data.data)
        layer0_repo.upsert_objects(table_id, objects)

        log.info("Processed batch", offset=offset)
