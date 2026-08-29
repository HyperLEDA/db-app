from dataclasses import dataclass


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
class Source:
    bibcode: str
    title: str
    authors: list[str]
    year: int


@dataclass
class AdditionalDesignation:
    name: str
    source: Source


@dataclass
class AdditionalDesignationsCatalog:
    names: list[AdditionalDesignation]


@dataclass
class NoteEntry:
    note: str
    source: Source


@dataclass
class NotesCatalog:
    notes: list[NoteEntry]


@dataclass
class PhotometryTotalMeasurement:
    band: str
    magsys: str | None
    method: str
    wavelength: float
    mag: float
    e_mag: float | None
    photsys: str
    filter: str


@dataclass
class PhotometryTotalCatalog:
    measurements: list[PhotometryTotalMeasurement]


@dataclass
class GeometryMeasurement:
    band: str
    method: str
    level: float | None
    a: float | None
    e_a: float | None
    b: float | None
    e_b: float | None
    pa: float | None
    e_pa: float | None
    isophote: float | None
    e_isophote: float | None
    source: Source


@dataclass
class GeometryCatalog:
    measurements: list[GeometryMeasurement]


@dataclass
class Catalogs:
    designation: DesignationCatalog | None = None
    additional_designations: AdditionalDesignationsCatalog | None = None
    icrs: ICRSCatalog | None = None
    redshift: RedshiftCatalog | None = None
    nature: NatureCatalog | None = None
    notes: NotesCatalog | None = None
    photometry_total: PhotometryTotalCatalog | None = None
    geometry: GeometryCatalog | None = None


@dataclass
class Layer2Object:
    pgc: int
    catalogs: Catalogs


__all__ = [
    "AdditionalDesignation",
    "AdditionalDesignationsCatalog",
    "Catalogs",
    "DesignationCatalog",
    "GeometryCatalog",
    "GeometryMeasurement",
    "ICRSCatalog",
    "Layer2Object",
    "NatureCatalog",
    "NoteEntry",
    "NotesCatalog",
    "PhotometryTotalCatalog",
    "PhotometryTotalMeasurement",
    "RedshiftCatalog",
    "Source",
]
