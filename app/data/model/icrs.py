from typing import Any, Self, final

from astropy import coordinates

from app.data.model import interface


@final
class ICRSCatalogObject(interface.CatalogObject):
    def __init__(
        self,
        ra: float | None = None,
        dec: float | None = None,
        e_ra: float | None = None,
        e_dec: float | None = None,
    ) -> None:
        self.ra = ra
        self.dec = dec
        self.e_ra = e_ra
        self.e_dec = e_dec

    @classmethod
    def from_custom(
        cls,
        ra: interface.MeasuredValue,
        dec: interface.MeasuredValue,
        e_ra: float | None = None,
        e_dec: float | None = None,
    ) -> Self:
        if not interface.is_nan(ra) and not interface.is_nan(dec):
            ra_angle = coordinates.Angle(ra.value, ra.unit)
            dec_angle = coordinates.Angle(dec.value, dec.unit)
        else:
            raise ValueError("no ra or dec values")

        if e_ra is None or e_dec is None:
            raise ValueError("no e_ra or e_dec specified")

        coords = coordinates.ICRS(ra=ra_angle, dec=dec_angle)

        return cls(coords.ra.deg, coords.dec.deg, e_ra, e_dec)

    def layer0_data(self) -> dict[str, Any]:
        return {
            "ra": self.ra,
            "dec": self.dec,
            "e_ra": self.e_ra,
            "e_dec": self.e_dec,
        }

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
        e_ras = [obj.e_ra for obj in objects if obj.e_ra is not None]
        decs = [obj.dec for obj in objects]
        e_decs = [obj.e_dec for obj in objects if obj.e_dec is not None]

        ra = sum(ras) / len(ras)
        e_ra = sum(e_ras) / len(e_ras) if e_ras else None
        dec = sum(decs) / len(decs)
        e_dec = sum(e_decs) / len(e_decs) if e_decs else None

        return cls(ra, dec, e_ra, e_dec)

    def catalog(self) -> interface.RawCatalog:
        return interface.RawCatalog.ICRS

    def layer1_data(self) -> dict[str, Any]:
        return {
            "ra": self.ra,
            "dec": self.dec,
            "e_ra": self.e_ra,
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
            "dec": self.dec,
            "e_ra": self.e_ra,
            "e_dec": self.e_dec,
        }

    @classmethod
    def from_layer2(cls, data: dict[str, Any]) -> Self:
        return cls(ra=data["ra"], e_ra=data["e_ra"], dec=data["dec"], e_dec=data["e_dec"])
