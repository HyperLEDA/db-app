from astropy import units as u

from app import entities
from app.data import model
from app.domain.model import Layer0Model
from app.lib.storage import enums, mapping


def layer_0_creation_mapper(domain: Layer0Model, bibliography_id: int) -> entities.Layer0Creation:
    """
    Maps Layer0 domain model to data creation model
    """
    descr_dict = dict([[d.column_name, d] for d in domain.meta.value_descriptions])
    columns = [
        entities.ColumnDescription(
            name=col_name,
            data_type=mapping.get_type_from_dtype(domain.data[col_name].dtype),
            unit=u.Unit(descr_dict.get(col_name).units) if descr_dict.get(col_name) is not None else None,
            ucd=descr_dict.get(col_name).ucd if descr_dict.get(col_name) is not None else None,
        )
        for col_name in domain.data.columns.values
    ]

    return entities.Layer0Creation(
        domain.id,
        columns,
        bibliography_id,
        enums.DataType.REGULAR,
        domain.meta.names_descr,
        domain.meta.comment,
    )


def layer_0_raw_mapper(domain: Layer0Model, table_id: int) -> model.Layer0RawData:
    """
    Maps Layer0 domain model to data raw data model
    """

    return model.Layer0RawData(table_id, domain.data)


def layer_0_bibliography_mapper(domain: Layer0Model) -> entities.Bibliography:
    """
    Maps Layer0 domain model to data bibliography data model
    """
    return entities.Bibliography(
        domain.meta.biblio.id,
        domain.meta.biblio.ref_str,
        domain.meta.biblio.year,
        domain.meta.biblio.authors,
        domain.meta.biblio.title,
    )
