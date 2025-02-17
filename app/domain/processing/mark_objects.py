import structlog

from app import entities
from app.data import model, repositories
from app.domain import converters

log: structlog.stdlib.BoundLogger = structlog.get_logger()


def mark_objects(layer0_repo: repositories.Layer0Repository, table_id: int, batch_size: int) -> None:
    meta = layer0_repo.fetch_metadata(table_id)
    convs = get_converters(meta.column_descriptions)
    for conv in convs:
        log.debug("Initialized converter", converter=conv.name())

    offset = 0

    while True:
        data = layer0_repo.fetch_raw_data(
            table_id, order_column=repositories.INTERNAL_ID_COLUMN_NAME, limit=batch_size, offset=offset
        )
        offset += min(batch_size, len(data.data))

        if len(data.data) == 0:
            break

        layer0_repo.upsert_objects(table_id, convert_rawdata_to_layer0_object(data, convs))

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


def get_converters(columns: list[entities.ColumnDescription]) -> list[converters.QuantityConverter]:
    convs = [
        converters.NameConverter(),
        converters.ICRSConverter(),
        converters.RedshiftConverter(),
    ]

    valid_converters = []

    for conv in convs:
        try:
            conv.parse_columns(columns)
        except converters.ConverterError:
            continue

        valid_converters.append(conv)

    return valid_converters
