from typing import Any, Self, final

import astropy.constants
from astropy import units as u

from app.data.model import interface


@final
class RedshiftCatalogObject(interface.CatalogObject):
    def __init__(
        self,
        cz: float,
        e_cz: float | None = None,
    ) -> None:
        self.cz = cz
        self.e_cz = e_cz

    @classmethod
    def from_custom(
        cls,
        cz: u.Quantity | None = None,
        z: float | None = None,
        e_cz: u.Quantity | float | None = None,
        e_z: float | None = None,
    ) -> Self:
        if not interface.is_nan(cz):
            data_cz = cz.to("m/s").value
        elif not interface.is_nan(z):
            data_cz = (z * astropy.constants.c).to("m/s").value
        else:
            raise ValueError("neither z nor cz is specified")

        if not interface.is_nan(e_cz):
            data_e_cz = e_cz.to("m/s").value
        elif not interface.is_nan(e_z):
            data_e_cz = (e_z * astropy.constants.c).to("m/s").value
        else:
            raise ValueError("neither e_z nor e_cz is specified")

        return cls(data_cz, data_e_cz)

    def layer0_data(self) -> dict[str, Any]:
        return {"cz": self.cz, "e_cz": self.e_cz}

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
