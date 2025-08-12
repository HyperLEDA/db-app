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


class HeliocentricVelocity(pydantic.BaseModel):
    v: float
    e_v: float


class Redshift(pydantic.BaseModel):
    z: float
    e_z: float


class Velocity(pydantic.BaseModel):
    heliocentric: HeliocentricVelocity
    redshift: Redshift


class Designation(pydantic.BaseModel):
    name: str


class Catalogs(pydantic.BaseModel):
    designation: Designation | None = None
    coordinates: Coordinates | None = None
    velocity: Velocity | None = None


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


class HeliocentricVelocityUnits(pydantic.BaseModel):
    v: str
    e_v: str


class VelocityUnits(pydantic.BaseModel):
    heliocentric: HeliocentricVelocityUnits


class Units(pydantic.BaseModel):
    coordinates: CoordinateUnits
    velocity: VelocityUnits


class Schema(pydantic.BaseModel):
    units: Units


class QuerySimpleRequest(pydantic.BaseModel):
    pgcs: list[int] | None = pydantic.Field(
        default=None,
        description="List of PGC numbers. If specified, all other filters will be ignored",
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


class QuerySimpleResponse(pydantic.BaseModel):
    objects: list[PGCObject]
    schema: Schema


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
    pgcs: list[int] | None = None
    ra: float | None = None
    dec: float | None = None
    radius: float | None = None
    name: str | None = None
    cz: float | None = None
    cz_err_percent: float | None = None
    page_size: int = 25
    page: int = 0


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
