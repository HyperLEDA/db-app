from app.domain.model import (
    CreateObjectBatchRequest,
    CreateObjectRequest,
    CreateObjectResponse,
)
from app.lib import exceptions
from app.presentation import actions


def create_object(r: CreateObjectRequest) -> CreateObjectResponse:
    response = actions.create_objects(
        CreateObjectBatchRequest(
            source_id=r.source_id,
            objects=[r.object],
        )
    )

    if len(response.ids) != 1:
        raise exceptions.new_internal_error("something went wrong during object creation")

    return CreateObjectResponse(id=response.ids[0])
