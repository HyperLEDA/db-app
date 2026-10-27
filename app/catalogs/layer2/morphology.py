from typing import Any, Self, final, override

from app.catalogs.layer1 import Catalog as Layer1Catalog
from app.catalogs.layer2 import interface


@final
class MorphologyCatalogObject(interface.CatalogObject):
    def __init__(self, t: float, em: float | None = None, ep: float | None = None) -> None:
        self.t = t
        self.em = em
        self.ep = ep

    @classmethod
    @override
    def catalog(cls) -> interface.Catalog:
        return interface.Catalog.MORPHOLOGY

    @classmethod
    @override
    def table(cls) -> str:
        return "layer2.morphology"

    @classmethod
    @override
    def sources(cls) -> list[Layer1Catalog]:
        return [Layer1Catalog.MORPHOLOGY__T]

    @classmethod
    @override
    def keys(cls) -> list[str]:
        return ["t", "em", "ep"]

    @override
    def to_row(self) -> dict[str, Any]:
        return {"t": self.t, "em": self.em, "ep": self.ep}

    @classmethod
    @override
    def from_row(cls, data: dict[str, Any]) -> Self:
        em = data["em"]
        ep = data["ep"]
        return cls(
            t=data["t"],
            em=None if em is None else float(em),
            ep=None if ep is None else float(ep),
        )
