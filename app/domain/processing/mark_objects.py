from collections.abc import Iterator

import structlog

from app.data import model, repositories
from app.domain import converters

log: structlog.stdlib.BoundLogger = structlog.get_logger()


def mark_objects(layer0_repo: repositories.Layer0Repository, table_id: int, batch_size: int) -> None:
    meta = layer0_repo.fetch_metadata(table_id)
    table_stats = layer0_repo.get_table_statistics(table_id)

    if (
        table_stats.total_rows == table_stats.total_original_rows
        and meta.modification_dt is not None
        and table_stats.last_modified_dt is not None
        and meta.modification_dt < table_stats.last_modified_dt
    ):
        log.info("Table was not modified since the last processing", table_id=table_id)
        return

    convs = get_converters(meta.column_descriptions)

    for data in object_batches(layer0_repo, table_id, batch_size):
        layer0_repo.upsert_objects(table_id, convert_rawdata_to_layer0_object(data, convs))


def object_batches(
    layer0_repo: repositories.Layer0Repository, table_id: int, batch_size: int
) -> Iterator[model.Layer0RawData]:
    offset = 0

    while True:
        data = layer0_repo.fetch_raw_data(
            table_id, order_column=repositories.INTERNAL_ID_COLUMN_NAME, limit=batch_size, offset=offset
        )
        offset += min(batch_size, len(data.data))

        if len(data.data) == 0:
            break

        yield data

        log.info("Processed batch", offset=offset)


def convert_rawdata_to_layer0_object(
    data: model.Layer0RawData, convs: list[converters.QuantityConverter]
) -> list[model.Layer0Object]:
    objects = []

    for obj_data in data.data.to_dict(orient="records"):
        layer0_obj = model.Layer0Object(object_id=obj_data[repositories.INTERNAL_ID_COLUMN_NAME], data=[])

        for conv in convs:
            try:
                obj = conv.apply(obj_data)
            except converters.ConverterError:
                continue

            layer0_obj.data.append(obj)

        objects.append(layer0_obj)

    return objects


def get_converters(columns: list[model.ColumnDescription]) -> list[converters.QuantityConverter]:
    convs: list[converters.QuantityConverter] = [
        converters.NameConverter(),
        converters.ICRSConverter(),
        converters.RedshiftConverter(),
    ]

    valid_converters = []

    for conv in convs:
        try:
            conv.parse_columns(columns)
            log.debug("Initialized converter", converter=conv.name())
        except converters.ConverterError as e:
            log.debug("Converter will not be used", converter=conv.name(), error=str(e))
            continue

        valid_converters.append(conv)

    if len(valid_converters) == 0:
        raise RuntimeError(
            "Unable to apply converters to the schema of the input table. Did you forget to validate it?"
        )

    return valid_converters
