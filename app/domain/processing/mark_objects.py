import uuid

import structlog

from app.data import model, repositories
from app.domain import homogenization
from app.domain.unification import modifiers
from app.lib import containers

log: structlog.stdlib.BoundLogger = structlog.get_logger()


def get_homogenization(
    repo: repositories.Layer0Repository,
    metadata: model.Layer0TableMeta,
    **kwargs,
) -> homogenization.Homogenization:
    db_rules = repo.get_homogenization_rules()
    db_params = repo.get_homogenization_params()

    rules = [new_rule(rule) for rule in db_rules]
    params = [new_params(param) for param in db_params]

    return homogenization.get_homogenization(rules, params, metadata, **kwargs)


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


def get_modificator(repo: repositories.Layer0Repository, table_name: str) -> modifiers.Applicator:
    db_modifiers = repo.get_modifiers(table_name)
    applicator = modifiers.Applicator()

    for m in db_modifiers:
        if m.modifier_name not in modifiers.registry:
            raise RuntimeError(f"no modifier with name {m.modifier_name} found")

        modifier = modifiers.registry[m.modifier_name](**m.params)
        applicator.add_modifier(m.column_name, modifier)

    return applicator


def mark_objects(
    layer0_repo: repositories.Layer0Repository,
    table_id: int,
    batch_size: int,
    cache_enabled: bool = True,
    initial_offset: str | None = None,
    ignore_homogenization_errors: bool = True,
) -> None:
    meta = layer0_repo.fetch_metadata(table_id)
    table_stats = layer0_repo.get_table_statistics(table_id)

    h = get_homogenization(layer0_repo, meta, ignore_errors=ignore_homogenization_errors)
    modificator = get_modificator(layer0_repo, meta.table_name)

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
        layer0_repo.fetch_table,
        lambda d: len(d) == 0,
        initial_offset,
        lambda d, _: list(d[repositories.INTERNAL_ID_COLUMN_NAME])[-1],  # type: ignore
        meta.table_name,
        order_column=repositories.INTERNAL_ID_COLUMN_NAME,
        batch_size=batch_size,
    ):
        data = modificator.apply(data)
        objects = h.apply(data)
        layer0_repo.upsert_objects(table_id, objects)

        last_uuid = uuid.UUID(offset or "00000000-0000-0000-0000-000000000000")
        max_uuid = uuid.UUID("FFFFFFFF-FFFF-FFFF-FFFF-FFFFFFFFFFFF")

        log.info(
            "Processed batch",
            last_object=offset,
            updated_count=len(objects),
            very_approximate_progress=f"{last_uuid.int / max_uuid.int * 100:.03f}%",
        )
