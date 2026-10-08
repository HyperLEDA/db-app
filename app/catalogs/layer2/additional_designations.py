from typing import final, override

from app.catalogs import layer1
from app.catalogs.layer2 import interface


@final
class AdditionalDesignationsCatalogObject(interface.CatalogObject):
    @classmethod
    @override
    def catalog(cls) -> interface.Catalog:
        return interface.Catalog.ADDITIONAL_DESIGNATIONS

    @classmethod
    @override
    def table(cls) -> str:
        return "layer2.designations"

    @classmethod
    @override
    def sources(cls) -> list[layer1.Catalog]:
        return [layer1.Catalog.DESIGNATION]
