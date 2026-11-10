from dataclasses import dataclass


@dataclass
class DesignationRecord:
    design: str


@dataclass
class ICRSRecord:
    ra: float
    e_ra: float
    dec: float
    e_dec: float


@dataclass
class RedshiftRecord:
    cz: float
    e_cz: float


@dataclass
class NatureRecord:
    type_name: str
