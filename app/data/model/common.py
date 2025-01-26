import enum

pgc = int


class RawCatalog(enum.Enum):
    """
    Enum that represents the catalogs in their original form. They are stored in two
    forms: one is the unaggregated collection of original data on layer 1 and the other is the
    aggregated data on layer 2.
    """

    ICRS = "icrs"
    DESIGNATION = "designation"


class Catalog(enum.Enum):
    """
    Enum that respesents catalogs that are physical quantities. They are obtained from
    raw catalogs on layer 2 by computing some physical quantity from the raw data.
    """
