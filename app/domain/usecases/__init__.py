import dataclasses
import datetime
from typing import Any, Callable, final

import structlog
from astroquery.vizier import Vizier

from app import data, domain
from app.data import interface
from app.data import model as data_model
from app.domain import model as domain_model
from app.domain import tasks
from app.domain.usecases.cross_identify_use_case import CrossIdentifyUseCase
from app.domain.usecases.transformation_0_1_use_case import TransformationO1UseCase
from app.lib.exceptions import (
    new_internal_error,
    new_not_found_error,
    new_validation_error,
)
from app.lib.storage import mapping, postgres

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
        if r.type != "publication":
            raise NotImplementedError("source types other than 'publication' are not supported yet")

        # TODO: this probably should be moved to API validation layer
        bibcode = r.metadata.get("bibcode")
        if bibcode is None:
            raise new_validation_error("bibcode is required in metadata for publication type")

        year = r.metadata.get("year")
        if year is None:
            raise new_validation_error("year is required in metadata for publication type")

        author = r.metadata.get("author")
        if author is None:
            raise new_validation_error("author is required in metadata for publication type")

        title = r.metadata.get("title")
        if title is None:
            raise new_validation_error("title is required in metadata for publication type")

        source_id = self._common_repo.create_bibliography(
            data_model.Bibliography(bibcode=bibcode, year=int(year), author=[author], title=title)
        )

        return domain_model.CreateSourceResponse(id=source_id)

    def get_source(self, r: domain_model.GetSourceRequest) -> domain_model.GetSourceResponse:
        result = self._common_repo.get_bibliography(r.id)

        return domain_model.GetSourceResponse(
            type="publication",
            metadata=dataclasses.asdict(result),
        )

    def get_source_list(self, r: domain_model.GetSourceListRequest) -> domain_model.GetSourceListResponse:
        if r.type != "publication":
            raise NotImplementedError("source types other than 'publication' are not supported yet")

        result = self._common_repo.get_bibliography_list(r.page * r.page_size, r.page_size)

        response = [
            domain_model.GetSourceResponse(
                type="publication",
                metadata=dataclasses.asdict(bib),
            )
            for bib in result
        ]
        return domain_model.GetSourceListResponse(response)

    def create_objects(self, r: domain_model.CreateObjectBatchRequest) -> domain_model.CreateObjectBatchResponse:
        with self._layer1_repo.with_tx() as tx:
            ids = self._layer1_repo.create_objects(len(r.objects), tx)

            self._layer1_repo.create_designations(
                [data_model.Designation(obj.name, r.source_id, pgc=id) for id, obj in zip(ids, r.objects)],
                tx,
            )

            self._layer1_repo.create_coordinates(
                [
                    data_model.CoordinateData(id, obj.position.coords.ra, obj.position.coords.dec, r.source_id)
                    for id, obj in zip(ids, r.objects)
                ],
                tx,
            )

        return domain_model.CreateObjectBatchResponse(ids)

    def create_object(self, r: domain_model.CreateObjectRequest) -> domain_model.CreateObjectResponse:
        response = self.create_objects(domain_model.CreateObjectBatchRequest(source_id=r.source_id, objects=[r.object]))

        if len(response.ids) != 1:
            raise new_internal_error(
                f"something went wrong during object creation, created {len(response.ids)} objects"
            )

        return domain_model.CreateObjectResponse(id=response.ids[0])

    def get_object_names(self, r: domain_model.GetObjectNamesRequest) -> domain_model.GetObjectNamesResponse:
        designations = self._layer1_repo.get_designations(r.id, r.page, r.page_size)

        if len(designations) == 0:
            raise new_not_found_error("object does not exist or has no designations")

        return domain_model.GetObjectNamesResponse(
            [
                domain_model.ObjectNameInfo(
                    designation.design,
                    designation.bib,
                    designation.modification_time or datetime.datetime.now(),
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
                fields = []

                for field in curr_table.fields:
                    fields.append(domain_model.Field(field.ID, field.description, str(field.unit)))

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
