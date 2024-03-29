import dataclasses
import datetime
import random
from typing import final

import numpy as np
import structlog
from astropy import table
from astroquery.vizier import Vizier
from numpy import ma

from app import data, domain
from app.data import model as data_model
from app.domain import model as domain_model
from app.domain.usecases.cross_identify_use_case import CrossIdentifyUseCase
from app.domain.usecases.transformation_0_1_use_case import TransformationO1UseCase
from app.lib.exceptions import (
    new_internal_error,
    new_not_found_error,
    new_validation_error,
)
from app.lib.storage import mapping

log: structlog.stdlib.BoundLogger = structlog.get_logger()


@final
class Actions(domain.Actions):
    def __init__(self, repo: data.Repository):
        self._repo = repo

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

        source_id = self._repo.create_bibliography(
            data_model.Bibliography(bibcode=bibcode, year=int(year), author=[author], title=title)
        )

        return domain_model.CreateSourceResponse(id=source_id)

    def get_source(self, r: domain_model.GetSourceRequest) -> domain_model.GetSourceResponse:
        result = self._repo.get_bibliography(r.id)

        return domain_model.GetSourceResponse(
            type="publication",
            metadata=dataclasses.asdict(result),
        )

    def get_source_list(self, r: domain_model.GetSourceListRequest) -> domain_model.GetSourceListResponse:
        if r.type != "publication":
            raise NotImplementedError("source types other than 'publication' are not supported yet")

        result = self._repo.get_bibliography_list(r.page * r.page_size, r.page_size)

        response = [
            domain_model.GetSourceResponse(
                type="publication",
                metadata=dataclasses.asdict(bib),
            )
            for bib in result
        ]
        return domain_model.GetSourceListResponse(response)

    def create_objects(self, r: domain_model.CreateObjectBatchRequest) -> domain_model.CreateObjectBatchResponse:
        with self._repo.with_tx() as tx:
            ids = self._repo.create_objects(len(r.objects), tx)

            self._repo.create_designations(
                [data_model.Designation(obj.name, r.source_id, pgc=id) for id, obj in zip(ids, r.objects)],
                tx,
            )

            self._repo.create_coordinates(
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
        designations = self._repo.get_designations(r.id, r.page, r.page_size)

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
                    log.warn("unable to find webpage in catalog meta", catalog=catalog_name)

                try:
                    bibcode = catalog["origin_article"][0]
                except KeyError:
                    log.warn("unable to find origin_article in catalog meta", catalog=catalog_name)

            except IndexError:
                log.warn("unable to find metadata for the catalog", catalog=catalog_name or catalog_key)

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

    def choose_table(self, r: domain_model.ChooseTableRequest) -> domain_model.ChooseTableResponse:
        Vizier.ROW_LIMIT = -1
        catalogs = Vizier.get_catalogs(r.catalog_id)
        catalog: table.Table | None = None

        for curr_catalog in catalogs:
            try:
                name = curr_catalog.meta["name"]
            except KeyError:
                continue

            if name != r.table_id:
                continue

            catalog = curr_catalog
            break

        if catalog is None:
            raise new_not_found_error("catalog or table you requested was not found")

        bad_fields = [field for field in catalog.columns if "-" in field]
        for bad_field in bad_fields:
            catalog[bad_field.replace("-", "_")] = catalog[bad_field]
            catalog.remove_column(bad_field)

        field: str
        for field in catalog.columns:
            if isinstance(catalog[field], ma.MaskedArray):
                if catalog[field].dtype == np.int16:
                    catalog[field] = catalog[field].filled(0)
                else:
                    catalog[field] = catalog[field].filled(np.nan)

        fields = []
        for field, field_meta in catalog.columns.items():
            t = mapping.get_type_from_dtype(field_meta.dtype)
            field = field.replace("-", "_")
            fields.append((field, t))

        table_id = random.randint(0, 2000000000)
        with self._repo.with_tx() as tx:
            self._repo.create_table("rawdata", f"data_{table_id}", fields, tx)

            raw_data = list(catalog)
            self._repo.insert_raw_data("rawdata", f"data_{table_id}", raw_data, tx)

        # TODO: save pipeline id to database?

        return domain_model.ChooseTableResponse(table_id)
