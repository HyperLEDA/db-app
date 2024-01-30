from dataclasses import dataclass
from typing import Optional

from .coordinates.coordinate_descr import CoordinateDescr
from .values.value_descr import ValueDescr
from .dataset import Dataset
from .biblio import Biblio


@dataclass
class Layer0Meta:
    """
    Metadata, used for transfer from layer 0 to layer 1
    Args:
        value_descriptions: List of implementations of [values.value_descr.ValueDescr], used to parse values from
        columns to astropy.units.Quantity, processed by level 1
        coordinateDescr: Implementation of coordinates.CoordinateDescr, used to parse coordinates correctly
        nameCol: Column, holding generally known name of the object
        dataset: Describes where data came from, measurements specifics
        comment: Optional comment
        biblio: Bibliographic information
    """
    value_descriptions: list[ValueDescr]
    coordinateDescr: Optional[CoordinateDescr]
    nameCol: Optional[str]
    dataset: Optional[Dataset]
    comment: Optional[str]
    biblio: Optional[Biblio]
