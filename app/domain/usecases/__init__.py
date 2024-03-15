import dataclasses
import logging
from typing import final

from app import data, domain
from app.data import model as data_model
from app.domain import model as domain_model
from app.domain.usecases.cross_identify_use_case import CrossIdentifyUseCase
from app.domain.usecases.transformation_0_1_use_case import TransformationO1UseCase
from app.lib.exceptions import new_validation_error


@final
class Actions(domain.Actions):
    def __init__(self, repo: data.Repository):
        self._repo = repo

    def create_source(self, r: domain_model.CreateSourceRequest) -> domain_model.CreateSourceResponse:
        if r.type != "publication":
            raise NotImplementedError("source types other that 'publication' are not supported yet")

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

        self._repo.create_bibliography(
            data_model.Bibliography(bibcode=bibcode, year=int(year), author=[author], title=title)
        )

        return domain_model.CreateSourceResponse(id=42)

    def get_source(self, r: domain_model.GetSourceRequest) -> domain_model.GetSourceResponse:
        logging.info(dataclasses.asdict(r))

        return domain_model.GetSourceResponse(type="table", metadata={"name": "haha funny name"})
