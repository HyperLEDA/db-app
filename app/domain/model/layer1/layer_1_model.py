from dataclasses import dataclass

from astropy.coordinates import SkyCoord

from app.domain.model.layer0 import Dataset
from app.domain.model.layer1.layer_1_value import Layer1Value


@dataclass
class Layer1Model:
    """
    Data model for layer 1 data. Represents one observation of concrete object
    Args:
        pgc: PGC. id of this object (e.g. galaxy). May be None, if Layer 2 object is not currently created (the object
            is just identified as new)
        source_id: Layer0Model id, from where this data came
        processed: True, if object processed, and data transformed further. False if not transformed, or changed after
            last transformation
        coordinates: SkyCoord frame in 'icrs'. Fully describes position on sky
        name: Generally known name of the object, may be used to identify objects in other data sources
        measurements: Measured values
        dataset: Describes where data came from, measurements specifics
    """

    pgc: int | None
    source_id: int
    processed: bool
    coordinates: SkyCoord | None
    name: str | None
    measurements: list[Layer1Value]
    dataset: Dataset | None
