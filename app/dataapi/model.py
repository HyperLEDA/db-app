from dataclasses import dataclass


@dataclass
class DesignationCatalog:
    name: str


@dataclass
class ObjectsCatalog:
    ra: float | None
    e_ra: float | None
    dec: float | None
    e_dec: float | None
    galactic_l: float | None
    galactic_b: float | None
    sgl: float | None
    sgb: float | None
    ebv: float | None


@dataclass
class RedshiftCatalog:
    cz: float
    e_cz: float


@dataclass
class Velocity:
    v: float
    e_v: float


@dataclass
class NatureCatalog:
    type_name: str


@dataclass
class MorphologyCatalog:
    t: float
    em: float | None
    ep: float | None


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
class Catalogs:
    designation: DesignationCatalog | None = None
    additional_designations: AdditionalDesignationsCatalog | None = None
    objects: ObjectsCatalog | None = None
    redshift: RedshiftCatalog | None = None
    nature: NatureCatalog | None = None
    morphology: MorphologyCatalog | None = None
    notes: NotesCatalog | None = None
    photometry_total: PhotometryTotalCatalog | None = None
    velocity: dict[str, Velocity] | None = None


@dataclass
class Layer2Object:
    pgc: int
    catalogs: Catalogs


__all__ = [
    "AdditionalDesignation",
    "AdditionalDesignationsCatalog",
    "Catalogs",
    "DesignationCatalog",
    "Layer2Object",
    "MorphologyCatalog",
    "NatureCatalog",
    "NoteEntry",
    "NotesCatalog",
    "ObjectsCatalog",
    "PhotometryTotalCatalog",
    "PhotometryTotalMeasurement",
    "RedshiftCatalog",
    "Source",
    "Velocity",
]
