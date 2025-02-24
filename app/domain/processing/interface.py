import abc
from typing import Any, final

from app.data import model
from app.data.repositories import layer2


class Crossmatcher(abc.ABC):
    """
    Base class for cross-identification processing.

    This class has a single responsibility: for a given object get layer 2 filters specific for this object.
    For example, for designation we might want to filter out objects with a similar designation.
    Or, for coordinates we might want to select objects with that are close to it.
    These filters are run later to get the possible PGC numbers of the objects.

    This abstraction does not correspond to CatalogObject one-to-one: the filtering might be
    as complex as needed across different types of data.
    For example, we might want to change the radius in the ICRS filter based on how large
    the object itself it using geometry catalog.
    """

    @staticmethod
    @abc.abstractmethod
    def name() -> str:
        """
        Name is necessary to identify the object in the result of the filtering on layer 2.
        """

    @staticmethod
    @abc.abstractmethod
    def get_search_params(obj: model.Layer0Object) -> dict[str, Any] | None:
        """
        Obtains parameters that will be used in search filters.
        If the objects does not have relevan parameters (i.e. does not have coordinates),
        None should be returned.

        These search parameters are used in the filters from `get_filter` method.
        """

    @abc.abstractmethod
    def get_filter(self) -> layer2.Filter:
        """
        Returns actual filters to get layer 2 objects.
        Filters may be as complex as needed, including a long chain of ANDs and ORs.
        """


@final
class DesignationCrossmatcher(Crossmatcher):
    def __init__(self, levenshtein_distance: int) -> None:
        self.dst = levenshtein_distance

    @staticmethod
    def name() -> str:
        return "designation"

    @staticmethod
    def get_search_params(obj: model.Layer0Object) -> dict[str, Any] | None:
        for catalog_obj in obj.data:
            if isinstance(catalog_obj, model.DesignationCatalogObject):
                return {"design": catalog_obj.designation}

        return None

    def get_filter(self) -> layer2.Filter:
        return layer2.DesignationCloseFilter(self.dst)


@final
class ICRSCrossmatcher(Crossmatcher):
    def __init__(self, radius_deg: float) -> None:
        self.radius = radius_deg

    @staticmethod
    def name() -> str:
        return "icrs"

    @staticmethod
    def get_search_params(obj: model.Layer0Object) -> dict[str, Any] | None:
        for catalog_obj in obj.data:
            if isinstance(catalog_obj, model.ICRSCatalogObject):
                return {"ra": catalog_obj.ra, "dec": catalog_obj.dec}

        return None

    def get_filter(self) -> layer2.Filter:
        return layer2.ICRSCoordinatesInRadiusFilter(self.radius)
