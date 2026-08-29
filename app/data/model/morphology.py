from typing import Any, final, override

from app.data.model import interface


@final
class MorphologyTCatalogObject(interface.CatalogObject):
    def __init__(
        self,
        value: int,
        method: str,
        em_value: float | None = None,
        ep_value: float | None = None,
        **kwargs: Any,
    ) -> None:
        self.value = value
        self.em_value = em_value
        self.ep_value = ep_value
        self.method = method

    @classmethod
    @override
    def catalog(cls) -> interface.RawCatalog:
        return interface.RawCatalog.MORPHOLOGY__T

    @classmethod
    def title(cls) -> str:
        return "Morphology (Hubble type)"

    @classmethod
    def description(cls) -> str:
        return "de Vaucouleurs numerical morphological types."

    @classmethod
    def layer1_table(cls) -> str:
        return "morphology.t"

    @classmethod
    def layer1_primary_keys(cls) -> list[str]:
        return ["record_id", "method"]


@final
class MorphologyFeaturesCatalogObject(interface.CatalogObject):
    def __init__(
        self,
        attribute_id: str,
        value: float,
        method: str,
        em_value: float | None = None,
        ep_value: float | None = None,
        **kwargs: Any,
    ) -> None:
        self.attribute_id = attribute_id
        self.value = value
        self.em_value = em_value
        self.ep_value = ep_value
        self.method = method

    @classmethod
    @override
    def catalog(cls) -> interface.RawCatalog:
        return interface.RawCatalog.MORPHOLOGY__FEATURES

    @classmethod
    def title(cls) -> str:
        return "Morphology (features)"

    @classmethod
    def description(cls) -> str:
        return "Morphological feature attributes."

    @classmethod
    def layer1_table(cls) -> str:
        return "morphology.features"

    @classmethod
    def layer1_primary_keys(cls) -> list[str]:
        return ["record_id", "attribute_id", "method"]


@final
class MorphologyExtraCatalogObject(interface.CatalogObject):
    def __init__(self, extra_type: str, **kwargs: Any) -> None:
        self.extra_type = extra_type

    @classmethod
    @override
    def catalog(cls) -> interface.RawCatalog:
        return interface.RawCatalog.MORPHOLOGY__EXTRA

    @classmethod
    def title(cls) -> str:
        return "Morphology (extra types)"

    @classmethod
    def description(cls) -> str:
        return "Additional morphological and phenomenological types."

    @classmethod
    def layer1_table(cls) -> str:
        return "morphology.extra"

    @classmethod
    def layer1_primary_keys(cls) -> list[str]:
        return ["record_id", "type"]


@final
class MorphologySpiralWindingCatalogObject(interface.CatalogObject):
    def __init__(
        self,
        winding: float,
        method: str,
        em_winding: float | None = None,
        ep_winding: float | None = None,
        **kwargs: Any,
    ) -> None:
        self.winding = winding
        self.em_winding = em_winding
        self.ep_winding = ep_winding
        self.method = method

    @classmethod
    @override
    def catalog(cls) -> interface.RawCatalog:
        return interface.RawCatalog.MORPHOLOGY__SPIRAL_WINDING

    @classmethod
    def title(cls) -> str:
        return "Morphology (spiral winding)"

    @classmethod
    def description(cls) -> str:
        return "Apparent spiral pattern winding direction."

    @classmethod
    def layer1_table(cls) -> str:
        return "morphology.spiral_winding"

    @classmethod
    def layer1_primary_keys(cls) -> list[str]:
        return ["record_id", "method"]
