from dataclasses import dataclass

from marshmallow import fields
from marshmallow_generic import GenericSchema


@dataclass
class EquatorialCoordinates:
    ra: float
    dec: float
    e_ra: float
    e_dec: float


@dataclass
class GalacticCoordinates:
    lon: float
    lat: float
    e_lon: float
    e_lat: float


@dataclass
class Coordinates:
    equatorial: EquatorialCoordinates
    galactic: GalacticCoordinates


@dataclass
class HeliocentricVelocity:
    v: float
    e_v: float


@dataclass
class Redshift:
    z: float
    e_z: float


@dataclass
class Velocity:
    heliocentric: HeliocentricVelocity
    redshift: Redshift


@dataclass
class Designation:
    name: str


@dataclass
class Catalogs:
    designation: Designation | None = None
    coordinates: Coordinates | None = None
    velocity: Velocity | None = None


@dataclass
class PGCObject:
    pgc: int
    catalogs: Catalogs


@dataclass
class EquatorialCoordinatesUnits:
    ra: str
    dec: str
    e_ra: str
    e_dec: str


@dataclass
class GalacticCoordinatesUnits:
    lon: str
    lat: str
    e_lon: str
    e_lat: str


@dataclass
class CoordinateUnits:
    equatorial: EquatorialCoordinatesUnits
    galactic: GalacticCoordinatesUnits


@dataclass
class HeliocentricVelocityUnits:
    v: str
    e_v: str


@dataclass
class VelocityUnits:
    heliocentric: HeliocentricVelocityUnits


@dataclass
class Units:
    coordinates: CoordinateUnits
    velocity: VelocityUnits


@dataclass
class Schema:
    units: Units


@dataclass
class DataResponse:
    objects: list[PGCObject]
    schema: Schema


@dataclass
class APIResponse:
    data: DataResponse


class EquatorialCoordinatesSchema(GenericSchema[EquatorialCoordinates]):
    ra = fields.Float(required=True)
    dec = fields.Float(required=True)
    e_ra = fields.Float(required=True)
    e_dec = fields.Float(required=True)


class GalacticCoordinatesSchema(GenericSchema[GalacticCoordinates]):
    lon = fields.Float(required=True)
    lat = fields.Float(required=True)
    e_lon = fields.Float(required=True)
    e_lat = fields.Float(required=True)


class CoordinatesSchema(GenericSchema[Coordinates]):
    equatorial = fields.Nested(EquatorialCoordinatesSchema, required=True)
    galactic = fields.Nested(GalacticCoordinatesSchema, required=True)


class HeliocentricVelocitySchema(GenericSchema[HeliocentricVelocity]):
    v = fields.Float(required=True)
    e_v = fields.Float(required=True)


class RedshiftSchema(GenericSchema[Redshift]):
    z = fields.Float(required=True)
    e_z = fields.Float(required=True)


class VelocitySchema(GenericSchema[Velocity]):
    heliocentric = fields.Nested(HeliocentricVelocitySchema, required=True)
    redshift = fields.Nested(RedshiftSchema, required=True)


class DesignationSchema(GenericSchema[Designation]):
    name = fields.String(required=True)


class CatalogsSchema(GenericSchema[Catalogs]):
    designation = fields.Nested(DesignationSchema)
    coordinates = fields.Nested(CoordinatesSchema)
    velocity = fields.Nested(VelocitySchema)


class PGCObjectSchema(GenericSchema[PGCObject]):
    pgc = fields.Integer(required=True)
    catalogs = fields.Nested(CatalogsSchema, required=True)


class EquatorialUnitsSchema(GenericSchema[EquatorialCoordinatesUnits]):
    ra = fields.String(required=True)
    dec = fields.String(required=True)
    e_ra = fields.String(required=True)
    e_dec = fields.String(required=True)


class GalacticUnitsSchema(GenericSchema[GalacticCoordinatesUnits]):
    lon = fields.String(required=True)
    lat = fields.String(required=True)
    e_lon = fields.String(required=True)
    e_lat = fields.String(required=True)


class CoordinateUnitsSchema(GenericSchema[CoordinateUnits]):
    equatorial = fields.Nested(EquatorialUnitsSchema, required=True)
    galactic = fields.Nested(GalacticUnitsSchema, required=True)


class HeliocentricVelocityUnitsSchema(GenericSchema[HeliocentricVelocityUnits]):
    v = fields.String(required=True)
    e_v = fields.String(required=True)


class VelocityUnitsSchema(GenericSchema[VelocityUnits]):
    heliocentric = fields.Nested(HeliocentricVelocityUnitsSchema, required=True)


class UnitsSchema(GenericSchema[Units]):
    coordinates = fields.Nested(CoordinateUnitsSchema, required=True)
    velocity = fields.Nested(VelocityUnitsSchema, required=True)


class SchemaSchema(GenericSchema[Schema]):
    units = fields.Nested(UnitsSchema, required=True)


class DataResponseSchema(GenericSchema[DataResponse]):
    objects = fields.List(fields.Nested(PGCObjectSchema), required=True)
    schema = fields.Nested(SchemaSchema, required=True)


class APIResponseSchema(GenericSchema[APIResponse]):
    data = fields.Nested(DataResponseSchema, required=True)
