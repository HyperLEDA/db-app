from typing import Any, Self, final

from app.data.model import interface


@final
class ICRSCatalogObject(interface.CatalogObject):
    def __init__(self, ra: float, e_ra: float, dec: float, e_dec: float, **kwargs) -> None:
        self.ra = ra
        self.e_ra = e_ra
        self.dec = dec
        self.e_dec = e_dec

    def __eq__(self, value: object) -> bool:
        if not isinstance(value, ICRSCatalogObject):
            return False

        return self.ra == value.ra and self.e_ra == value.e_ra and self.dec == value.dec and self.e_dec == value.e_dec

    @classmethod
    def aggregate(cls, objects: list[Self]) -> Self:
        """
        Aggregate coordinates are computed as the mean of all coordinates.
        Errors are computed as the mean of all errors.
        """
        ras = [obj.ra for obj in objects]
        e_ras = [obj.e_ra for obj in objects]
        decs = [obj.dec for obj in objects]
        e_decs = [obj.e_dec for obj in objects]

        ra = sum(ras) / len(ras)
        e_ra = sum(e_ras) / len(e_ras)
        dec = sum(decs) / len(decs)
        e_dec = sum(e_decs) / len(e_decs)

        return cls(ra, e_ra, dec, e_dec)

    def catalog(self) -> interface.RawCatalog:
        return interface.RawCatalog.ICRS

    def layer1_data(self) -> dict[str, Any]:
        return {
            "ra": self.ra,
            "e_ra": self.e_ra,
            "dec": self.dec,
            "e_dec": self.e_dec,
        }

    @classmethod
    def layer1_table(cls) -> str:
        return "icrs.data"

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
            "e_ra": self.e_ra,
            "dec": self.dec,
            "e_dec": self.e_dec,
        }

    @classmethod
    def from_layer2(cls, data: dict[str, Any]) -> Self:
        return cls(ra=data["ra"], e_ra=data["e_ra"], dec=data["dec"], e_dec=data["e_dec"])
