from dataclasses import dataclass

from app.data.model import interface


@dataclass
class Layer1Observation:
    object_id: str
    catalog_object: interface.CatalogObject


@dataclass
class Layer1PGCObservation:
    pgc: int
    observation: Layer1Observation
