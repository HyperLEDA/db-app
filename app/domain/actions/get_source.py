from app import commands, schema


def get_source(depot: commands.Depot, r: schema.GetSourceRequest) -> schema.GetSourceResponse:
    result = depot.common_repo.get_bibliography(r.id)

    return schema.GetSourceResponse(
        result.code,
        result.title,
        result.author,
        result.year,
    )
