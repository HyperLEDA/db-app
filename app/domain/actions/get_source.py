from app import schema
from app.commands.adminapi import depot


def get_source(dpt: depot.Depot, r: schema.GetSourceRequest) -> schema.GetSourceResponse:
    result = dpt.common_repo.get_source_by_id(r.id)

    return schema.GetSourceResponse(
        result.code,
        result.title,
        result.author,
        result.year,
    )
