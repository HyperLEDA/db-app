from typing import Any, final, override

from app.catalogs.layer1 import interface


@final
class DistanceCatalogObject(interface.CatalogObject):
    def __init__(
        self,
        modulus: float,
        calib_id: str,
        em_modulus: float | None = None,
        ep_modulus: float | None = None,
        quality: str = "regular",
        **kwargs: Any,
    ) -> None:
        self.modulus = modulus
        self.em_modulus = em_modulus
        self.ep_modulus = ep_modulus
        self.quality = quality
        self.calib_id = calib_id

    @classmethod
    @override
    def catalog(cls) -> interface.Catalog:
        return interface.Catalog.DISTANCE

    @classmethod
    def title(cls) -> str:
        return "Distance"

    @classmethod
    def description(cls) -> str:
        return "Redshift-independent distance measurements."

    @classmethod
    def layer1_table(cls) -> str:
        return "distance.data"

    @classmethod
    def layer1_primary_keys(cls) -> list[str]:
        return ["record_id", "calib_id"]
