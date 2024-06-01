import datetime
from typing import Any, Callable, final

import pandas

from app import commands, domain
from app.data import model as data_model
from app.domain import model as domain_model
from app.domain import tasks
from app.domain.usecases.cross_identify_use_case import CrossIdentifyUseCase
from app.domain.usecases.store_l0_use_case import StoreL0UseCase
from app.domain.usecases.transaction_0_1_use_case import Transaction01UseCase
from app.domain.usecases.transformation_0_1_use_case import TransformationO1UseCase
from app.lib.exceptions import new_not_found_error, new_unauthorized_error, new_validation_error
from app.lib.storage import enums, mapping, postgres

__all__ = ["Actions", "CrossIdentifyUseCase", "TransformationO1UseCase", "StoreL0UseCase", "Transaction01UseCase"]

TASK_REGISTRY: dict[str, tuple[Callable, Any]] = {
    "echo": (tasks.echo_task, tasks.EchoTaskParams),
    "download_vizier_table": (tasks.download_vizier_table, tasks.DownloadVizierTableParams),
}


@final
class Actions(domain.Actions):
    def __init__(
        self,
        depot: commands.Depot,
        # remove this when actions are split
        storage_config: postgres.PgStorageConfig,
    ) -> None:
        self.depot = depot
        self._storage_config = storage_config

    def create_source(self, r: domain_model.CreateSourceRequest) -> domain_model.CreateSourceResponse:
        if r.bibcode is not None:
            try:
                publication = self.depot.clients.ads.query_simple(f'bibcode:"{r.bibcode}"')[0]

                r.title = publication["title"][0]
                r.authors = list(publication["author"])
                r.year = (
                    datetime.datetime.strptime(publication["pubdate"], "%Y-%m-00")
                    .astimezone(datetime.timezone.utc)
                    .year
                )
            except RuntimeError as e:
                raise new_validation_error("no search results returned for bibcode from ADS") from e

        source_id = self.depot.common_repo.create_bibliography(
            data_model.Bibliography(bibcode=r.bibcode, year=r.year, author=r.authors, title=r.title)
        )

        return domain_model.CreateSourceResponse(id=source_id)

    def get_source(self, r: domain_model.GetSourceRequest) -> domain_model.GetSourceResponse:
        result = self.depot.common_repo.get_bibliography(r.id)

        return domain_model.GetSourceResponse(
            result.bibcode,
            result.title,
            result.author,
            result.year,
        )

    def start_task(self, r: domain_model.StartTaskRequest) -> domain_model.StartTaskResponse:
        if r.task_name not in TASK_REGISTRY:
            raise new_not_found_error(f"unable to find task '{r.task_name}'")

        task, params_type = TASK_REGISTRY[r.task_name]

        params = params_type(**r.payload)

        with self.depot.common_repo.with_tx() as tx:
            task_id = self.depot.common_repo.insert_task(data_model.Task(r.task_name, r.payload, 1), tx)
            self.depot.queue_repo.enqueue(
                tasks.task_runner,
                func=task,
                task_id=task_id,
                storage_config=self._storage_config,
                params=params,
            )

        return domain_model.StartTaskResponse(task_id)

    def get_task_info(self, r: domain_model.GetTaskInfoRequest) -> domain_model.GetTaskInfoResponse:
        task_info = self.depot.common_repo.get_task_info(r.task_id)
        return domain_model.GetTaskInfoResponse(
            task_info.id,
            task_info.task_name,
            str(task_info.status.value),
            task_info.payload,
            task_info.start_time,
            task_info.end_time,
            task_info.message,
        )

    def create_table(self, r: domain_model.CreateTableRequest) -> domain_model.CreateTableResponse:
        columns = []

        for col in r.columns:
            try:
                col_type = mapping.get_type(col.data_type)
            except ValueError as e:
                raise new_validation_error(str(e)) from e

            columns.append(
                data_model.ColumnDescription(
                    name=col.name, data_type=col_type, unit=col.unit, description=col.description
                )
            )

        with self.depot.layer0_repo.with_tx() as tx:
            table_id = self.depot.layer0_repo.create_table(
                data_model.Layer0Creation(
                    table_name=r.table_name,
                    column_descriptions=columns,
                    bibliography_id=r.bibliography_id,
                    datatype=enums.DataType(r.datatype),
                    comment=r.description,
                ),
                tx=tx,
            )

        return domain_model.CreateTableResponse(table_id)

    def add_data(self, r: domain_model.AddDataRequest) -> domain_model.AddDataResponse:
        data_df = pandas.DataFrame.from_records(r.data)

        with self.depot.layer0_repo.with_tx() as tx:
            self.depot.layer0_repo.insert_raw_data(
                data_model.Layer0RawData(
                    table_id=r.table_id,
                    data=data_df,
                ),
                tx=tx,
            )

        return domain_model.AddDataResponse()

    def login(self, r: domain_model.LoginRequest) -> domain_model.LoginResponse:
        token, is_authenticated = self.depot.authenticator.login(r.username, r.password)

        if not is_authenticated:
            raise new_unauthorized_error("invalid username or password")

        return domain_model.LoginResponse(token=token)
