import dataclasses
from typing import final

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
        # TODO: this whole method should be a single transaction. Context manager in storage?
        ids = self._repo.create_objects(len(r.objects))

        self._repo.create_designations(
            [data_model.Designation(obj.name, r.source_id, pgc=id) for id, obj in zip(ids, r.objects)],
        )

        self._repo.create_coordinates(
            [
                data_model.CoordinateData(id, obj.position.coords.ra, obj.position.coords.dec, r.source_id)
                for id, obj in zip(ids, r.objects)
            ]
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
                domain_model.ObjectNameInfo(designation.design, designation.bib, designation.modification_time)
                for designation in designations
            ]
        )