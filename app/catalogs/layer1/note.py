from typing import final, override

from app.catalogs.layer1 import interface


@final
class NoteCatalogObject(interface.CatalogObject):
    @classmethod
    @override
    def catalog(cls) -> interface.Catalog:
        return interface.Catalog.NOTE

    @classmethod
    def title(cls) -> str:
        return "Note"

    @classmethod
    def description(cls) -> str:
        return "Free-text notes attached to records."
