from dataclasses import dataclass
from astropy.units import Quantity
from abc import ABC


@dataclass
class Layer1Value(ABC):
    """
    Some value (measurement) of concrete data type (e.g. km/s).
    Args:
        value: astropy.units.Quantity, representing a value, and it's unit
        ucd: UCD (https://www.ivoa.net/documents/REC/VOTable/VOTable-20040811.html#ToC28) key,
            describing this value type, and maps to Layer0Meta.columnMap
    """
    value: Quantity
    ucd: str
