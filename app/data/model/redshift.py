from typing import Any, Self, final

import astropy.constants
import numpy as np

from app.data.model import interface


@final
class RedshiftCatalogObject(interface.CatalogObject):
    def __init__(
        self,
        z: float | None = None,
        e_z: float | None = None,
        cz: float | None = None,
        e_cz: float | None = None,
        **kwargs,
    ) -> None:
        if z is not None and not np.isnan(z):
            cz = z * astropy.constants.c.to("m/s").value
            e_cz = e_z * astropy.constants.c.to("m/s").value if e_z is not None else None

        if cz is None:
            raise ValueError("neither z nor cz is specified")

        self.cz = cz
        self.e_cz = e_cz

    @classmethod
    def aggregate(cls, objects: list[Self]) -> Self:
        e_cz = [obj.e_cz for obj in objects if obj.e_cz is not None]

        cz = sum(obj.cz for obj in objects) / len(objects)
        e_cz = sum(e_cz) / len(e_cz) if e_cz else None

        return cls(cz, e_cz)

    def catalog(self) -> interface.RawCatalog:
        return interface.RawCatalog.REDSHIFT

    @classmethod
    def layer1_table(cls) -> str:
        return "cz.data"

    @classmethod
    def layer1_keys(cls) -> list[str]:
        return ["cz", "e_cz"]

    def layer1_data(self) -> dict[str, Any]:
        return {"cz": self.cz, "e_cz": self.e_cz}

    @classmethod
    def from_layer1(cls, data: dict[str, Any]) -> Self:
        return cls(cz=data["cz"], e_cz=data["e_cz"])

    @classmethod
    def layer2_table(cls) -> str:
        return "layer2.cz"

    @classmethod
    def layer2_keys(cls) -> list[str]:
        return ["cz", "e_cz"]

    def layer2_data(self) -> dict[str, Any]:
        return {"cz": self.cz, "e_cz": self.e_cz}

    @classmethod
    def from_layer2(cls, data: dict[str, Any]) -> Self:
        return cls(cz=data["cz"], e_cz=data["e_cz"])
