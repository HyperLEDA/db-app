from typing import final, override

from app.catalogs import layer1
from app.catalogs.layer2 import interface


@final
class PhotometryTotalCatalogObject(interface.CatalogObject):
    @classmethod
    @override
    def catalog(cls) -> interface.Catalog:
        return interface.Catalog.PHOTOMETRY__TOTAL

    @classmethod
    @override
    def table(cls) -> str:
        return "layer2.photometry_total"

    @classmethod
    @override
    def sources(cls) -> list[layer1.Catalog]:
        return [layer1.Catalog.PHOTOMETRY__TOTAL]
