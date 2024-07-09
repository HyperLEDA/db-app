from app.data.model import Bibliography, ColumnDescription, Layer0Creation, Layer0RawData
from app.data.model.layer0 import CoordinatePart
from app.domain.model import Layer0Model
from app.lib.storage import enums, mapping


def layer_0_creation_mapper(domain: Layer0Model, bibliography_id: int) -> Layer0Creation:
    """
    Maps Layer0 domain model to data creation model
    """
    descr_dict = dict([[d.column_name, d] for d in domain.meta.value_descriptions])
    return Layer0Creation(
        domain.id,
        [
            ColumnDescription(
                name=col_name,
                data_type=mapping.get_type_from_dtype(domain.data[col_name].dtype),
                unit=descr_dict.get(col_name).units if descr_dict.get(col_name) is not None else None,
                coordinate_part=CoordinatePart(
                    domain.meta.coordinate_descr.description_id(),
                    domain.meta.coordinate_descr.arg_number(col_name),
                    col_name,
                )
                if domain.meta.coordinate_descr.arg_number(col_name) is not None
                else None,
                ucd=descr_dict.get(col_name).ucd if descr_dict.get(col_name) is not None else None,
            )
            for col_name in domain.data.columns.values
        ],
        bibliography_id,
        enums.DataType.REGULAR,
        domain.meta.names_descr,
        domain.meta.comment,
    )


def layer_0_raw_mapper(domain: Layer0Model, table_id: int) -> Layer0RawData:
    """
    Maps Layer0 domain model to data raw data model
    """

    return Layer0RawData(table_id, domain.data)


def layer_0_bibliography_mapper(domain: Layer0Model) -> Bibliography:
    """
    Maps Layer0 domain model to data bibliography data model
    """
    return Bibliography(
        domain.meta.biblio.ref_str,
        domain.meta.biblio.year,
        domain.meta.biblio.authors,
        domain.meta.biblio.title,
        domain.meta.biblio.id,
    )
