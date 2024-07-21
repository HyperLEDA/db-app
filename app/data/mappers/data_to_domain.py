from app.data.model import Bibliography, ColumnDescription, Layer0Creation, Layer0RawData
from app.domain.model import Layer0Model
from app.domain.model.layer0.biblio import Biblio
from app.domain.model.layer0.coordinates import ICRSDescrStr
from app.domain.model.layer0.coordinates.icrs_descr import ICRS_DESCR_ID
from app.domain.model.layer0.layer_0_meta import Layer0Meta
from app.domain.model.layer0.values import NoErrorValue
from app.domain.model.layer0.values.value_descr import ValueDescr


def layer_0_mapper(creation: Layer0Creation, raw: Layer0RawData, bibliography: Bibliography) -> Layer0Model:
    coordinate_cols = [it.coordinate_part for it in creation.column_descriptions if it.coordinate_part is not None]
    coordinate_cols.sort(key=lambda it: it.arg_num)

    coordinate_descr = None
    if len(coordinate_cols) > 0:
        if all(it.descr_id == ICRS_DESCR_ID for it in coordinate_cols):
            coordinate_descr = ICRSDescrStr(*[it.column_name for it in coordinate_cols])

    meta = Layer0Meta(
        list(filter(lambda it: it is not None, [_make_value_descr(descr) for descr in creation.column_descriptions])),
        coordinate_descr,
        creation.name_col,
        None,
        creation.comment,
        Biblio(bibliography.id, bibliography.code, bibliography.author, bibliography.year, bibliography.title),
    )

    return Layer0Model(creation.table_name, False, meta, raw.data)


def _make_value_descr(descr: ColumnDescription) -> ValueDescr | None:
    if descr.ucd is None:
        return None

    return NoErrorValue(descr.ucd, descr.name, descr.unit)
