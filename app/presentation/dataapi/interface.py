import abc

import pydantic


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


class Coordinates(pydantic.BaseModel):
    equatorial: EquatorialCoordinates
    galactic: GalacticCoordinates


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


class CoordinateUnits(pydantic.BaseModel):
    equatorial: EquatorialCoordinatesUnits
    galactic: GalacticCoordinatesUnits


class AbsoluteVelocityUnits(pydantic.BaseModel):
    v: str
    e_v: str


class Units(pydantic.BaseModel):
    coordinates: CoordinateUnits
    velocity: dict[str, AbsoluteVelocityUnits]


class Schema(pydantic.BaseModel):
    units: Units


class QuerySimpleRequest(pydantic.BaseModel):
    pgcs: list[int] | None = pydantic.Field(
        default=None,
        description="List of PGC numbers. If specified, no other filters are allowed",
    )
    ra: float | None = pydantic.Field(
        default=None,
        description="Right ascension of the center of the search area in degrees",
    )
    dec: float | None = pydantic.Field(
        default=None,
        description="Declination of the center of the search area in degrees",
    )
    radius: float | None = pydantic.Field(
        default=None,
        description="Radius of the search area in degrees",
    )
    name: str | None = pydantic.Field(
        default=None,
        description="Name of the object",
    )
    cz: float | None = pydantic.Field(
        default=None,
        description="Redshift value",
    )
    cz_err_percent: float | None = pydantic.Field(
        default=None,
        description="Acceptable deviation of the redshift value in percent",
    )
    page_size: int = pydantic.Field(
        default=25,
        description="Number of objects per page",
    )
    page: int = pydantic.Field(
        default=0,
        description="Page number",
    )

    @pydantic.model_validator(mode="after")
    def _pgcs_exclusive_with_filters(self) -> "QuerySimpleRequest":
        if self.pgcs:
            filters = [self.ra, self.dec, self.radius, self.name, self.cz, self.cz_err_percent]
            if any(f is not None for f in filters):
                raise ValueError("When pgcs is specified, no other filters are allowed")
        return self


class QuerySimpleResponse(pydantic.BaseModel):
    objects: list[PGCObject]
    schema_: Schema = pydantic.Field(alias="schema")


class QueryRequest(pydantic.BaseModel):
    q: str = pydantic.Field(
        description="Query string",
    )
    page_size: int = pydantic.Field(
        default=10,
        description="Number of objects per page",
    )
    page: int = pydantic.Field(
        default=0,
        description="Page number",
    )


class QueryResponse(pydantic.BaseModel):
    objects: list[PGCObject]


class FITSRequest(pydantic.BaseModel):
    pgcs: list[int] | None = pydantic.Field(
        default=None,
        description="List of PGC numbers",
    )
    ra: float | None = pydantic.Field(
        default=None,
        description="Right ascension of the center of the search area in degrees",
    )
    dec: float | None = pydantic.Field(
        default=None,
        description="Declination of the center of the search area in degrees",
    )
    radius: float | None = pydantic.Field(
        default=None,
        description="Radius of the search area in degrees",
    )
    name: str | None = pydantic.Field(
        default=None,
        description="Name of the object",
    )
    cz: float | None = pydantic.Field(
        default=None,
        description="Redshift value",
    )
    cz_err_percent: float | None = pydantic.Field(
        default=None,
        description="Acceptable deviation of the redshift value in percent",
    )
    page_size: int = pydantic.Field(
        default=25,
        description="Number of objects per page",
    )
    page: int = pydantic.Field(
        default=0,
        description="Page number",
    )


class Actions(abc.ABC):
    @abc.abstractmethod
    def query_simple(self, query: QuerySimpleRequest) -> QuerySimpleResponse:
        pass

    @abc.abstractmethod
    def query(self, query: QueryRequest) -> QueryResponse:
        pass

    @abc.abstractmethod
    def query_fits(self, query: FITSRequest) -> bytes:
        pass
