import abc
import datetime
from dataclasses import dataclass, field
from typing import Any

from app.lib.storage import enums


@dataclass
class GetTaskInfoRequest:
    task_id: int


@dataclass
class GetTaskInfoResponse:
    id: int | None
    task_name: str
    status: str
    payload: dict[str, Any]
    start_time: datetime.datetime | None
    end_time: datetime.datetime | None
    message: dict[str, Any] | None


@dataclass
class ColumnDescription:
    name: str
    data_type: str
    ucd: str | None = None
    unit: str | None = None
    description: str | None = None


@dataclass
class CreateTableRequest:
    table_name: str
    columns: list[ColumnDescription]
    bibcode: str
    datatype: str
    description: str


@dataclass
class CreateTableResponse:
    id: int


@dataclass
class AddDataRequest:
    table_id: int
    data: list[dict[str, Any]]


@dataclass
class AddDataResponse:
    pass


@dataclass
class GetTableValidationRequest:
    table_id: int


@dataclass
class TableValidation:
    validator: str
    message: str


@dataclass
class GetTableValidationResponse:
    validations: list[TableValidation]


@dataclass
class CrossIdentification:
    inner_radius_arcsec: float = 1.5
    outer_radius_arcsec: float = 3


@dataclass
class TableProcessRequest:
    table_id: int
    cross_identification: CrossIdentification = field(default_factory=CrossIdentification)
    batch_size: int = 100


@dataclass
class TableProcessResponse:
    pass


@dataclass
class TableStatusStatsRequest:
    table_id: int


@dataclass
class TableStatusStatsResponse:
    processing: dict[enums.ObjectProcessingStatus, int]


@dataclass
class SetTableStatusOverrides:
    id: str
    pgc: int | None = None


@dataclass
class SetTableStatusRequest:
    table_id: int
    overrides: list[SetTableStatusOverrides] | None = None
    batch_size: int = 100


@dataclass
class SetTableStatusResponse:
    pass


@dataclass
class CreateSourceRequest:
    title: str
    authors: list[str]
    year: int


@dataclass
class CreateSourceResponse:
    code: str


@dataclass
class LoginRequest:
    username: str
    password: str


@dataclass
class LoginResponse:
    token: str


class Actions(abc.ABC):
    @abc.abstractmethod
    def add_data(self, request: AddDataRequest) -> AddDataResponse:
        pass

    @abc.abstractmethod
    def create_table(self, request: CreateTableRequest) -> tuple[CreateTableResponse, bool]:
        pass

    @abc.abstractmethod
    def get_table_validation(self, request: GetTableValidationRequest) -> GetTableValidationResponse:
        pass

    @abc.abstractmethod
    def create_source(self, request: CreateSourceRequest) -> CreateSourceResponse:
        pass

    @abc.abstractmethod
    def set_table_status(self, request: SetTableStatusRequest) -> SetTableStatusResponse:
        pass

    @abc.abstractmethod
    def table_process(self, request: TableProcessRequest) -> TableProcessResponse:
        pass

    @abc.abstractmethod
    def table_status_stats(self, request: TableStatusStatsRequest) -> TableStatusStatsResponse:
        pass

    @abc.abstractmethod
    def get_task_info(self, request: GetTaskInfoRequest) -> GetTaskInfoResponse:
        pass

    @abc.abstractmethod
    def login(self, request: LoginRequest) -> LoginResponse:
        pass
