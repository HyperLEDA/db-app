from typing import Any, Self, final, override

from app.data.model import interface


@final
class ICRSCatalogObject(interface.CatalogObject):
    def __init__(
        self,
        ra: float,
        dec: float,
        e_ra: float,
        e_dec: float,
    ) -> None:
        self.ra = ra
        self.dec = dec
        self.e_ra = e_ra
        self.e_dec = e_dec

    @classmethod
    @override
    def catalog(cls) -> interface.RawCatalog:
        return interface.RawCatalog.ICRS

    @classmethod
    def title(cls) -> str:
        return "ICRS"

    @classmethod
    def description(cls) -> str:
        return "Equatorial coordinates in the ICRS frame."

    @classmethod
    def layer1_keys(cls) -> list[str]:
        return ["ra", "e_ra", "dec", "e_dec"]

    @classmethod
    def from_layer1(cls, data: dict[str, Any]) -> Self:
        return cls(ra=data["ra"], e_ra=data["e_ra"], dec=data["dec"], e_dec=data["e_dec"])

    @classmethod
    def layer2_table(cls) -> str:
        return "layer2.icrs"

    @classmethod
    def layer2_keys(cls) -> list[str]:
        return ["ra", "e_ra", "dec", "e_dec"]

    def layer2_data(self) -> dict[str, Any]:
        return {
            "ra": self.ra,
            "dec": self.dec,
            "e_ra": self.e_ra,
            "e_dec": self.e_dec,
        }

    @classmethod
    def from_layer2(cls, data: dict[str, Any]) -> Self:
        return cls(ra=data["ra"], e_ra=data["e_ra"], dec=data["dec"], e_dec=data["e_dec"])
