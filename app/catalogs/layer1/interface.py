import abc
import enum
from typing import Any, Self


class Catalog(enum.Enum):
    ICRS = "icrs"
    DESIGNATION = "designation"
    REDSHIFT = "redshift"
    NATURE = "nature"
    PHOTOMETRY__TOTAL = "photometry_total"
    PHOTOMETRY__ISOPHOTAL = "photometry_isophotal"
    GEOMETRY = "geometry"
    SPECTROSCOPY__INTEGRATED_FLUX_DENSITY = "spectroscopy_integrated_flux_density"
    SPECTROSCOPY__ENERGY_FLUX = "spectroscopy_energy_flux"
    KINEMATICS__LINE_WIDTH = "kinematics_line_width"
    DISTANCE = "distance"
    MORPHOLOGY__T = "morphology_t"
    MORPHOLOGY__FEATURES = "morphology_features"
    MORPHOLOGY__EXTRA = "morphology_extra"
    MORPHOLOGY__SPIRAL_WINDING = "morphology_spiral_winding"
    NOTE = "note"


class CatalogObject(abc.ABC):
    @classmethod
    @abc.abstractmethod
    def catalog(cls) -> Catalog: ...

    @classmethod
    @abc.abstractmethod
    def title(cls) -> str: ...

    @classmethod
    @abc.abstractmethod
    def description(cls) -> str: ...

    @classmethod
    def layer1_table(cls) -> str:
        catalog = cls.catalog()
        return f"{catalog.value}.data"

    @classmethod
    def layer1_keys(cls) -> list[str]:
        raise NotImplementedError

    @classmethod
    def layer1_primary_keys(cls) -> list[str]:
        return ["record_id"]

    @classmethod
    def from_layer1(cls, data: dict[str, Any]) -> Self:
        raise NotImplementedError
