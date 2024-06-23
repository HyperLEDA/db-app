from app import commands
from app.domain import model as domain_model


def get_source(depot: commands.Depot, r: domain_model.GetSourceRequest) -> domain_model.GetSourceResponse:
    result = depot.common_repo.get_bibliography(r.id)

    return domain_model.GetSourceResponse(
        result.bibcode,
        result.title,
        result.author,
        result.year,
    )
