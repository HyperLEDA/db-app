from typing import Any, Self, final

from app.data.model import interface


@final
class PGCCatalogObject(interface.CatalogObject):
    def __init__(self, pgc: int | None) -> None:
        self.pgc = pgc

    @classmethod
    def aggregate(cls, objects: list[Self]) -> Self:
        return cls(pgc=objects[0].pgc)

    def catalog(self) -> interface.RawCatalog:
        return interface.RawCatalog.PGC

    @classmethod
    def layer1_table(cls) -> str:
        return "pgc.data"

    def layer1_data(self) -> dict[str, Any]:
        if self.pgc is None:
            return {}

        return {"id": self.pgc}

    @classmethod
    def from_layer1(cls, data: dict[str, Any]) -> Self:
        return cls(pgc=data["id"])

    @classmethod
    def layer2_table(cls) -> str:
        return "layer2.pgc"

    @classmethod
    def layer2_keys(cls) -> list[str]:
        return ["pgc"]

    def layer2_data(self) -> dict[str, Any]:
        return {"pgc": self.pgc}

    @classmethod
    def from_layer2(cls, data: dict[str, Any]) -> Self:
        return cls(pgc=data["pgc"])
