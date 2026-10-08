from typing import final, override

from app.catalogs.layer1 import Catalog as Layer1Catalog
from app.catalogs.layer2 import interface


@final
class NoteCatalogObject(interface.CatalogObject):
    @classmethod
    @override
    def catalog(cls) -> interface.Catalog:
        return interface.Catalog.NOTE

    @classmethod
    @override
    def table(cls) -> str:
        return "layer2.notes"

    @classmethod
    @override
    def sources(cls) -> list[Layer1Catalog]:
        return [Layer1Catalog.NOTE]
