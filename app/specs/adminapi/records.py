import enum
from typing import Any

import pydantic


class UploadStatus(enum.Enum):
    UPLOADED = "uploaded"
    PENDING = "pending"


class CrossmatchTriageStatus(enum.Enum):
    UNPROCESSED = "unprocessed"
    PENDING = "pending"
    RESOLVED = "resolved"


class GetRecordsRequest(pydantic.BaseModel):
    table_name: str
    page: int = 0
    page_size: int = 25
    pgc: int | None = None
    upload_status: UploadStatus | None = None
    triage_status: CrossmatchTriageStatus | None = None

    @pydantic.model_validator(mode="after")
    def check_exclusive_pgc_filter(self) -> "GetRecordsRequest":
        if self.pgc is not None:
            if any([self.upload_status is not None, self.triage_status is not None]):
                raise ValueError("When pgc filter is specified, no other filters are allowed.")
        return self

    @pydantic.model_validator(mode="after")
    def check_upload_status_and_triage_status(self) -> "GetRecordsRequest":
        if self.upload_status == UploadStatus.UPLOADED and self.triage_status is not None:
            raise ValueError("When upload_status is UPLOADED, triage_status is not allowed.")
        return self


class RecordCrossmatchCandidate(pydantic.BaseModel):
    pgc: int


class RecordCrossmatchInfo(pydantic.BaseModel):
    triage_status: CrossmatchTriageStatus
    candidates: list[RecordCrossmatchCandidate]


class RecordDesignationCatalog(pydantic.BaseModel):
    name: str


class RecordICRSCatalog(pydantic.BaseModel):
    ra: float
    ra_error: float
    dec: float
    dec_error: float


class RecordRedshiftCatalog(pydantic.BaseModel):
    z: float
    z_error: float


class RecordNatureCatalog(pydantic.BaseModel):
    type_name: str


class RecordCatalogValues(pydantic.BaseModel):
    designation: RecordDesignationCatalog | None
    icrs: RecordICRSCatalog | None
    redshift: RecordRedshiftCatalog | None
    nature: RecordNatureCatalog | None


class Record(pydantic.BaseModel):
    id: str
    original_data: dict[str, Any]
    pgc: int | None
    crossmatch: RecordCrossmatchInfo
    catalogs: RecordCatalogValues


class RecordOriginalDataSchema(pydantic.BaseModel):
    description: dict[str, str]
    ucd: dict[str, str]
    unit: dict[str, str]


class RecordDesignationCatalogDescriptionSchema(pydantic.BaseModel):
    name: str


class RecordDesignationCatalogSchema(pydantic.BaseModel):
    description: RecordDesignationCatalogDescriptionSchema


class RecordICRSCatalogUnitSchema(pydantic.BaseModel):
    ra: str
    ra_error: str
    dec: str
    dec_error: str


class RecordICRSCatalogDescriptionSchema(pydantic.BaseModel):
    ra: str
    ra_error: str
    dec: str
    dec_error: str


class RecordICRSCatalogSchema(pydantic.BaseModel):
    unit: RecordICRSCatalogUnitSchema
    description: RecordICRSCatalogDescriptionSchema


class RecordRedshiftCatalogDescriptionSchema(pydantic.BaseModel):
    z: str
    z_error: str


class RecordRedshiftCatalogSchema(pydantic.BaseModel):
    description: RecordRedshiftCatalogDescriptionSchema


class RecordNatureCatalogDescriptionSchema(pydantic.BaseModel):
    type_name: str
    types: dict[str, str] = pydantic.Field(description="Mapping of type keys to their descriptions")


class RecordNatureCatalogSchema(pydantic.BaseModel):
    description: RecordNatureCatalogDescriptionSchema


class RecordCatalogSchema(pydantic.BaseModel):
    designation: RecordDesignationCatalogSchema
    icrs: RecordICRSCatalogSchema
    redshift: RecordRedshiftCatalogSchema
    nature: RecordNatureCatalogSchema


class RecordSchema(pydantic.BaseModel):
    original_data: RecordOriginalDataSchema
    catalogs: RecordCatalogSchema


class GetRecordsResponse(pydantic.BaseModel):
    records: list[Record]
    schema_: RecordSchema = pydantic.Field(..., alias="schema")
