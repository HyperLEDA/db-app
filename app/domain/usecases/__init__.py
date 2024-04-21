import datetime
from typing import Any, Callable, final

import structlog
from astroquery.vizier import Vizier

from app import domain
from app.data import interface
from app.data import model as data_model
from app.domain import model as domain_model
from app.domain import tasks
from app.domain.usecases.cross_identify_use_case import CrossIdentifyUseCase
from app.domain.usecases.transformation_0_1_use_case import TransformationO1UseCase
from app.lib.exceptions import new_not_found_error
from app.lib.storage import enums, mapping, postgres

__all__ = [
    "Actions",
    "CrossIdentifyUseCase",
    "TransformationO1UseCase",
]

TASK_REGISTRY: dict[str, tuple[Callable, Any]] = {
    "echo": (tasks.echo_task, tasks.EchoTaskParams),
    "download_vizier_table": (tasks.download_vizier_table, tasks.DownloadVizierTableParams),
}


@final
class Actions(domain.Actions):
    def __init__(
        self,
        common_repo: interface.CommonRepository,
        layer0_repo: interface.Layer0Repository,
        layer1_repo: interface.Layer1Repository,
        queue_repo: interface.QueueRepository,
        # remove this when actions are split
        storage_config: postgres.PgStorageConfig,
        logger: structlog.stdlib.BoundLogger,
    ) -> None:
        self._common_repo = common_repo
        self._layer0_repo = layer0_repo
        self._layer1_repo = layer1_repo
        self._queue_repo = queue_repo
        self._storage_config = storage_config
        self._logger = logger

    def create_source(self, r: domain_model.CreateSourceRequest) -> domain_model.CreateSourceResponse:
        source_id = self._common_repo.create_bibliography(
            data_model.Bibliography(bibcode=r.bibcode, year=r.year, author=r.authors, title=r.title)
        )

        return domain_model.CreateSourceResponse(id=source_id)

    def get_source(self, r: domain_model.GetSourceRequest) -> domain_model.GetSourceResponse:
        result = self._common_repo.get_bibliography(r.id)

        return domain_model.GetSourceResponse(
            result.bibcode,
            result.title,
            result.author,
            result.year,
        )

    def get_source_list(self, r: domain_model.GetSourceListRequest) -> domain_model.GetSourceListResponse:
        result = self._common_repo.get_bibliography_list(r.title, r.page * r.page_size, r.page_size)

        response = [
            domain_model.GetSourceResponse(
                bib.bibcode,
                bib.title,
                bib.author,
                bib.year,
            )
            for bib in result
        ]
        return domain_model.GetSourceListResponse(response)

    def get_object_names(self, r: domain_model.GetObjectNamesRequest) -> domain_model.GetObjectNamesResponse:
        designations = self._layer1_repo.get_designations(r.id, r.page, r.page_size)

        if len(designations) == 0:
            raise new_not_found_error("object does not exist or has no designations")

        return domain_model.GetObjectNamesResponse(
            [
                domain_model.ObjectNameInfo(
                    designation.design,
                    designation.bib,
                    designation.modification_time or datetime.datetime.now(tz=datetime.UTC),
                )
                for designation in designations
            ]
        )

    def search_catalogs(self, r: domain_model.SearchCatalogsRequest) -> domain_model.SearchCatalogsResponse:
        catalogs = Vizier.find_catalogs(r.query)

        catalogs_info = []
        for catalog_key, catalog_info in catalogs.items():
            url = ""
            bibcode = ""

            try:
                # TODO: this is a clutch, need to find a way to get catalog name reasonably
                catalog_name = "/".join(catalog_key.split("/")[:-1])
                catalog = Vizier.get_catalog_metadata(catalog=catalog_name)
                try:
                    url = catalog["webpage"][0]
                except KeyError:
                    self._logger.warn("unable to find webpage in catalog meta", catalog=catalog_name)

                try:
                    bibcode = catalog["origin_article"][0]
                except KeyError:
                    self._logger.warn("unable to find origin_article in catalog meta", catalog=catalog_name)

            except IndexError:
                self._logger.warn("unable to find metadata for the catalog", catalog=catalog_name or catalog_key)

            tables = []

            for curr_table in catalog_info.tables:
                fields = [
                    domain_model.Field(field.ID, field.description, str(field.unit)) for field in curr_table.fields
                ]
                tables.append(
                    domain_model.Table(
                        id=curr_table.ID,
                        num_rows=curr_table.nrows,
                        fields=fields,
                    )
                )

            catalogs_info.append(
                domain_model.Catalog(
                    id=catalog_key,
                    description=catalog_info.description,
                    url=url,
                    bibcode=bibcode,
                    tables=tables,
                )
            )

        return domain_model.SearchCatalogsResponse(catalogs=catalogs_info)

    def start_task(self, r: domain_model.StartTaskRequest) -> domain_model.StartTaskResponse:
        if r.task_name not in TASK_REGISTRY:
            raise new_not_found_error(f"unable to find task '{r.task_name}'")

        task, params_type = TASK_REGISTRY[r.task_name]

        params = params_type(**r.payload)

        with self._common_repo.with_tx() as tx:
            task_id = self._common_repo.insert_task(data_model.Task(r.task_name, r.payload, 1), tx)
            self._queue_repo.enqueue(
                tasks.task_runner,
                func=task,
                task_id=task_id,
                storage_config=self._storage_config,
                params=params,
            )

        return domain_model.StartTaskResponse(task_id)

    def debug_start_task(self, r: domain_model.StartTaskRequest) -> domain_model.StartTaskResponse:
        if r.task_name not in TASK_REGISTRY:
            raise new_not_found_error(f"unable to find task '{r.task_name}'")

        task, params_type = TASK_REGISTRY[r.task_name]

        params = params_type(**r.payload)

        with self._common_repo.with_tx() as tx:
            task_id = self._common_repo.insert_task(data_model.Task(r.task_name, r.payload, 1), tx)
            tasks.task_runner(
                func=task,
                task_id=task_id,
                storage_config=self._storage_config,
                params=params,
            )

        return domain_model.StartTaskResponse(task_id)

    def get_task_info(self, r: domain_model.GetTaskInfoRequest) -> domain_model.GetTaskInfoResponse:
        task_info = self._common_repo.get_task_info(r.task_id)
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
            columns.append(
                data_model.ColumnDescription(
                    name=col.name,
                    data_type=mapping.get_type(col.data_type),
                    unit=col.unit,
                    description=col.description,
                )
            )

        with self._layer0_repo.with_tx() as tx:
            table_id = self._layer0_repo.create_table(
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
