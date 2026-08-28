from collections.abc import Callable
from typing import Annotated, Any

import pydantic
from astropy import units as u
from pydantic import AfterValidator, BeforeValidator, WithJsonSchema

from app.lib import astronomy

__all__ = [
    "AbsoluteVelocity",
    "AbsoluteVelocityUnits",
    "AdditionalDesignation",
    "CalculateReddeningRequest",
    "CalculateReddeningResponse",
    "Catalogs",
    "CoordinateUnits",
    "Coordinates",
    "Designation",
    "EquatorialCoordinates",
    "EquatorialCoordinatesUnits",
    "GalacticCoordinates",
    "GalacticCoordinatesUnits",
    "J2000Coordinate",
    "Nature",
    "NoteEntry",
    "PGCObject",
    "PhotometryTotalMeasurement",
    "QuerySimpleRequest",
    "QuerySimpleResponse",
    "ReddeningAtPosition",
    "ReddeningFilterValue",
    "Redshift",
    "Schema",
    "Source",
    "SupergalacticCoordinates",
    "SupergalacticCoordinatesUnits",
    "Units",
]


def _degree_to_float(value: u.Quantity) -> float:
    return float(value.to_value(u.Unit("deg")))


def _as_deg(value: Any) -> u.Quantity:
    if isinstance(value, u.Quantity):
        return value.to(u.Unit("deg"))
    return float(value) * u.Unit("deg")


def _in_range(low: float, high: float | None = None) -> Callable[[u.Quantity], u.Quantity]:
    def validate(value: u.Quantity) -> u.Quantity:
        degrees = _degree_to_float(value)
        if high is None:
            if degrees <= low:
                raise ValueError(f"Input should be greater than {low}")
        elif not low <= degrees <= high:
            raise ValueError(f"Input should be in [{low}, {high}]")
        return value

    return validate


class EquatorialCoordinates(pydantic.BaseModel):
    ra: float
    dec: float
    e_ra: float
    e_dec: float


class GalacticCoordinates(pydantic.BaseModel):
    lon: float
    lat: float
    e_lon: float
    e_lat: float


class SupergalacticCoordinates(pydantic.BaseModel):
    lon: float
    lat: float
    e_lon: float
    e_lat: float


class Coordinates(pydantic.BaseModel):
    equatorial: EquatorialCoordinates
    galactic: GalacticCoordinates
    supergalactic: SupergalacticCoordinates


class AbsoluteVelocity(pydantic.BaseModel):
    v: float
    e_v: float


class Redshift(pydantic.BaseModel):
    z: float
    e_z: float


class Designation(pydantic.BaseModel):
    name: str


class Source(pydantic.BaseModel):
    bibcode: str
    title: str
    authors: list[str]
    year: int


class AdditionalDesignation(pydantic.BaseModel):
    name: str
    source: Source


class NoteEntry(pydantic.BaseModel):
    note: str
    source: Source


class PhotometryTotalMeasurement(pydantic.BaseModel):
    band: str
    magsys: str | None
    method: str
    wavelength: float
    mag: float
    e_mag: float | None


class Nature(pydantic.BaseModel):
    type_name: str


class Catalogs(pydantic.BaseModel):
    designation: Designation | None = None
    additional_designations: list[AdditionalDesignation] | None = None
    coordinates: Coordinates | None = None
    velocity: dict[str, AbsoluteVelocity] | None = None
    redshift: Redshift | None = None
    nature: Nature | None = None
    notes: list[NoteEntry] | None = None
    photometry_total: list[PhotometryTotalMeasurement] | None = None


class PGCObject(pydantic.BaseModel):
    pgc: int
    catalogs: Catalogs


class EquatorialCoordinatesUnits(pydantic.BaseModel):
    ra: str
    dec: str
    e_ra: str
    e_dec: str


class GalacticCoordinatesUnits(pydantic.BaseModel):
    lon: str
    lat: str
    e_lon: str
    e_lat: str


class SupergalacticCoordinatesUnits(pydantic.BaseModel):
    lon: str
    lat: str
    e_lon: str
    e_lat: str


class CoordinateUnits(pydantic.BaseModel):
    equatorial: EquatorialCoordinatesUnits
    galactic: GalacticCoordinatesUnits
    supergalactic: SupergalacticCoordinatesUnits


class AbsoluteVelocityUnits(pydantic.BaseModel):
    v: str
    e_v: str


class Units(pydantic.BaseModel):
    coordinates: CoordinateUnits
    velocity: dict[str, AbsoluteVelocityUnits]


class Schema(pydantic.BaseModel):
    units: Units


class QuerySimpleRequest(pydantic.BaseModel):
    model_config = pydantic.ConfigDict(arbitrary_types_allowed=True)

    pgcs: list[int] | None = pydantic.Field(
        default=None,
        description="List of PGC numbers. If specified, no other filters are allowed",
    )
    ra: (
        Annotated[
            u.Quantity,
            BeforeValidator(_as_deg),
            AfterValidator(_in_range(0, 360)),
            WithJsonSchema({"type": "number"}),
        ]
        | None
    ) = pydantic.Field(
        default=None,
        description="Right ascension of the center of the search area in degrees [0, 360]",
    )
    dec: (
        Annotated[
            u.Quantity,
            BeforeValidator(_as_deg),
            AfterValidator(_in_range(-90, 90)),
            WithJsonSchema({"type": "number"}),
        ]
        | None
    ) = pydantic.Field(
        default=None,
        description="Declination of the center of the search area in degrees [-90, 90]",
    )
    glon: (
        Annotated[
            u.Quantity,
            BeforeValidator(_as_deg),
            AfterValidator(_in_range(0, 360)),
            WithJsonSchema({"type": "number"}),
        ]
        | None
    ) = pydantic.Field(
        default=None,
        description="Galactic longitude of the center of the search area in degrees [0, 360]",
    )
    glat: (
        Annotated[
            u.Quantity,
            BeforeValidator(_as_deg),
            AfterValidator(_in_range(-90, 90)),
            WithJsonSchema({"type": "number"}),
        ]
        | None
    ) = pydantic.Field(
        default=None,
        description="Galactic latitude of the center of the search area in degrees [-90, 90]",
    )
    sgl: (
        Annotated[
            u.Quantity,
            BeforeValidator(_as_deg),
            AfterValidator(_in_range(0, 360)),
            WithJsonSchema({"type": "number"}),
        ]
        | None
    ) = pydantic.Field(
        default=None,
        description="Supergalactic longitude of the center of the search area in degrees [0, 360]",
    )
    sgb: (
        Annotated[
            u.Quantity,
            BeforeValidator(_as_deg),
            AfterValidator(_in_range(-90, 90)),
            WithJsonSchema({"type": "number"}),
        ]
        | None
    ) = pydantic.Field(
        default=None,
        description="Supergalactic latitude of the center of the search area in degrees [-90, 90]",
    )
    radius: (
        Annotated[
            u.Quantity,
            BeforeValidator(_as_deg),
            AfterValidator(_in_range(0)),
            WithJsonSchema({"type": "number"}),
        ]
        | None
    ) = pydantic.Field(
        default=None,
        description="Radius of the search area in degrees (must be > 0)",
    )
    eq_epoch: str = pydantic.Field(
        default="J2000",
        description="Equinox of equatorial query coordinates (e.g. J2000, B1950)",
    )
    name: str | None = pydantic.Field(
        default=None,
        description="Name of the object",
    )
    page_size: int = pydantic.Field(
        default=25,
        description="Number of objects per page",
    )
    page: int = pydantic.Field(
        default=0,
        description="0-based page number",
    )
    catalogs: list[str] | None = pydantic.Field(
        default=None,
        description=(
            "Catalogs to include in the response (e.g. designation, icrs, redshift, nature). "
            "If omitted, default set of catalogs is returned."
        ),
    )

    @pydantic.field_validator("eq_epoch")
    @classmethod
    def _validate_eq_epoch(cls, value: str) -> str:
        astronomy.parse_coordinate_epoch(value)
        return value

    @pydantic.model_validator(mode="after")
    def _coordinate_sets(self) -> "QuerySimpleRequest":
        if (self.ra is None) != (self.dec is None):
            raise ValueError("ra and dec must be specified together")
        if (self.glon is None) != (self.glat is None):
            raise ValueError("glon and glat must be specified together")
        if (self.sgl is None) != (self.sgb is None):
            raise ValueError("sgl and sgb must be specified together")

        systems = [
            self.ra is not None,
            self.glon is not None,
            self.sgl is not None,
        ]
        if sum(systems) > 1:
            raise ValueError(
                "Only one coordinate system may be specified: "
                "equatorial (ra/dec), galactic (glon/glat), or supergalactic (sgl/sgb)"
            )
        if self.radius is not None and sum(systems) == 0:
            raise ValueError(
                "When radius is specified, at least one coordinate set must be specified: "
                "equatorial (ra/dec), galactic (glon/glat), or supergalactic (sgl/sgb)"
            )
        return self

    @pydantic.model_validator(mode="after")
    def _pgcs_exclusive_with_filters(self) -> "QuerySimpleRequest":
        if self.pgcs:
            filters = [
                self.ra,
                self.dec,
                self.glon,
                self.glat,
                self.sgl,
                self.sgb,
                self.radius,
                self.name,
            ]
            if any(f is not None for f in filters):
                raise ValueError("When pgcs is specified, no other filters are allowed")
        return self


class QuerySimpleResponse(pydantic.BaseModel):
    objects: list[PGCObject]
    schema_: Schema = pydantic.Field(alias="schema")


class J2000Coordinate(pydantic.BaseModel):
    ra: float = pydantic.Field(ge=0, lt=360)
    dec: float = pydantic.Field(ge=-90, le=90)


class ReddeningFilterValue(pydantic.BaseModel):
    filter: str
    wavelength: float
    a: float


class ReddeningAtPosition(pydantic.BaseModel):
    ebv: float
    filters: list[ReddeningFilterValue]


class CalculateReddeningRequest(pydantic.BaseModel):
    photsys: str
    coordinates: list[J2000Coordinate] = pydantic.Field(min_length=1, max_length=10_000)


class CalculateReddeningResponse(pydantic.BaseModel):
    photsys: str
    results: list[ReddeningAtPosition]
