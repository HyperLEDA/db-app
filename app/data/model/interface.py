import abc
import enum
from typing import Any, Self


class RawCatalog(enum.Enum):
    """
    Enum that represents the catalogs in their original form. They are stored in two
    forms: one is the unaggregated collection of original data on layer 1 and the other is the
    aggregated data on layer 2.
    """

    ICRS = "icrs"
    DESIGNATION = "designation"
    ADDITIONAL_DESIGNATIONS = "additional_designations"
    REDSHIFT = "redshift"
    NATURE = "nature"
    PHOTOMETRY__TOTAL = "photometry_total"
    PHOTOMETRY__ISOPHOTAL = "photometry_isophotal"
    GEOMETRY = "geometry"
    NOTE = "note"
    RADIO = "radio"


RUNTIME_RAW_CATALOGS: frozenset[RawCatalog] = frozenset(
    {
        RawCatalog.ADDITIONAL_DESIGNATIONS,
    }
)


class CatalogObject(abc.ABC):
    """
    Represents an object stored in a particular catalog.
    """

    @abc.abstractmethod
    def catalog(self) -> RawCatalog:
        """Return the catalog identifier. Required for every catalog."""

    @classmethod
    def layer1_table(cls) -> str:
        """Return the layer 1 table name.

        Override when the table is not named ``{catalog.value}.data``, for example
        ``cz.data`` for redshift or ``photometry.ellipse`` for geometry.
        """
        catalog = object.__new__(cls).catalog()
        return f"{catalog.value}.data"

    @classmethod
    def layer1_keys(cls) -> list[str]:
        """Return layer 1 payload column names (excluding ``record_id``).

        Override when layer 1 rows are read back through ``query_records()``, e.g.
        in the crossmatch API. The list should include only catalog data columns,
        not internal columns such as ``modification_time``.
        """
        raise NotImplementedError

    @classmethod
    def layer1_primary_keys(cls) -> list[str]:
        """Return columns used for upsert conflict resolution on layer 1.

        Override when a record can have multiple rows in the same table, for example
        multiple designations per record or photometry per band.
        """
        return ["record_id"]

    @classmethod
    def from_layer1(cls, data: dict[str, Any]) -> Self:
        """Build a catalog object from a layer 1 row.

        Override together with ``layer1_keys()`` when layer 1 data is read through
        ``query_records()``.
        """
        raise NotImplementedError

    @classmethod
    def layer2_table(cls) -> str:
        """Return the layer 2 table or view name.

        Override when the catalog is aggregated to layer 2, used by import tasks,
        layer 2 queries, and table progress reporting.
        """
        raise NotImplementedError

    @classmethod
    def layer2_keys(cls) -> list[str]:
        """Return layer 2 payload column names (excluding ``pgc``).

        Override together with ``layer2_table()`` when the catalog participates in
        layer 2 aggregation or querying.
        """
        raise NotImplementedError

    def layer2_data(self) -> dict[str, Any]:
        """Serialize this object to layer 2 column values.

        Override when writing aggregated data to layer 2, for example in import
        tasks or FITS export.
        """
        raise NotImplementedError

    @classmethod
    def from_layer2(cls, data: dict[str, Any]) -> Self:
        """Build a catalog object from a layer 2 row.

        Override together with ``layer2_table()`` and ``layer2_keys()`` when layer 2
        data is queried through ``Layer2Repository``.
        """
        raise NotImplementedError


def get_object[T](catalog_objects: list[CatalogObject], t: type[T]) -> T | None:
    for obj in catalog_objects:
        if isinstance(obj, t):
            return obj

    return None
