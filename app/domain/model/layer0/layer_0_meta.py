from dataclasses import dataclass
from typing import Optional

from app.domain.model.layer0.biblio import Biblio
from app.domain.model.layer0.coordinates.coordinate_descr import CoordinateDescr
from app.domain.model.layer0.dataset import Dataset
from app.domain.model.layer0.values.value_descr import ValueDescr


@dataclass
class Layer0Meta:
    """
    Metadata, used for transfer from layer 0 to layer 1
    Args:
        value_descriptions: List of implementations of [values.value_descr.ValueDescr], used to parse values from
        columns to astropy.units.Quantity, processed by level 1
        coordinate_descr: Implementation of coordinates.CoordinateDescr, used to parse coordinates correctly
        name_col: Column, holding generally known name of the object
        dataset: Describes where data came from, measurements specifics
        comment: Optional comment
        biblio: Bibliographic information
    """

    value_descriptions: list[ValueDescr]
    coordinate_descr: Optional[CoordinateDescr]
    name_col: Optional[str]
    dataset: Optional[Dataset]
    comment: Optional[str]
    biblio: Optional[Biblio]
