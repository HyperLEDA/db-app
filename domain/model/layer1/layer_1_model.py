from dataclasses import dataclass
from astropy.coordinates import SkyCoord
from typing import Optional


from .layer_1_value import Layer1Value
from ..layer0 import Dataset


@dataclass
class Layer1Model:
    """
    Data model for layer 1 data. Represents one observation of concrete object
    Args:
        id: This observation id
        objectId: id of this object (e.g. galaxy)
        sourceId: Layer0Model id, from where this data came
        processed: True, if object processed, and data transformed further. False if not transformed, or changed after
            last transformation
        coordinates: SkyCoord frame in 'icrs'. Fully describes position on sky
        name: Generally known name of the object, may be used to identify objects in other data sources
        measurements: Measured values
        dataset: Describes where data came from, measurements specifics
    """
    id: int
    objectId: int
    sourceId: int
    processed: bool
    coordinates: Optional[SkyCoord]
    name: Optional[str]
    measurements: list[Layer1Value]
    dataset: Optional[Dataset]
