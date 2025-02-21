import abc

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

    @abc.abstractmethod
    def get_filter(self, obj: model.Layer0Object) -> layer2.Filter | None:
        """
        Returns actual filters to get layer 2 objects.
        Filters may be as complex as needed, including a long chain of ANDs and ORs.
        """


class DesignationCrossmatcher(Crossmatcher):
    def __init__(self, levenshtein_distance: int) -> None:
        self.dst = levenshtein_distance

    @staticmethod
    def name() -> str:
        return "designation"

    def get_filter(self, obj: model.Layer0Object) -> layer2.Filter | None:
        for catalog_object in obj.data:
            if isinstance(catalog_object, model.DesignationCatalogObject):
                return layer2.DesignationCloseFilter(catalog_object.designation, self.dst)

        return None


class ICRSCrossmatcher(Crossmatcher):
    def __init__(self, radius_deg: float) -> None:
        self.radius = radius_deg

    @staticmethod
    def name() -> str:
        return "icrs"

    def get_filter(self, obj: model.Layer0Object) -> layer2.Filter | None:
        for catalog_object in obj.data:
            if isinstance(catalog_object, model.ICRSCatalogObject):
                return layer2.ICRSCoordinatesInRadiusFilter(
                    catalog_object.ra, catalog_object.dec, self.radius
                )

        return None
