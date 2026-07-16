from typing import final

from app.data.model import interface


@final
class RadioCatalogObject(interface.CatalogObject):
    def catalog(self) -> interface.RawCatalog:
        return interface.RawCatalog.RADIO
