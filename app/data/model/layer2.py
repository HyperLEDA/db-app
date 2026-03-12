from dataclasses import dataclass

from app.data.model import interface


@dataclass
class Layer2CatalogObject:
    pgc: int
    data: list[interface.CatalogObject]

    def get[T](self, t: type[T]) -> T | None:
        for obj in self.data:
            if isinstance(obj, t):
                return obj

        return None


@dataclass
class DesignationCatalog:
    name: str


@dataclass
class ICRSCatalog:
    ra: float
    e_ra: float
    dec: float
    e_dec: float


@dataclass
class RedshiftCatalog:
    cz: float
    e_cz: float


@dataclass
class NatureCatalog:
    type_name: str


@dataclass
class Catalogs:
    """
    Dsscription of catalogs as they are stored on layer 2. To properly analyze them one probably needs
    to read units from metadata of these tables.
    """

    designation: DesignationCatalog | None = None
    icrs: ICRSCatalog | None = None
    redshift: RedshiftCatalog | None = None
    nature: NatureCatalog | None = None


@dataclass
class Layer2Object:
    pgc: int
    catalogs: Catalogs
