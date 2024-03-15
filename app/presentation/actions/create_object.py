from app.presentation import actions
from app.presentation.model import (
    CreateObjectBatchRequest,
    CreateObjectRequest,
    CreateObjectResponse,
)
from app.presentation.server.exceptions import new_internal_error


def create_object(r: CreateObjectRequest) -> CreateObjectResponse:
    response = actions.create_objects(
        CreateObjectBatchRequest(
            source_id=r.source_id,
            objects=[r.object],
        )
    )

    if len(response.ids) != 1:
        raise new_internal_error("something went wrong during object creation")

    return CreateObjectResponse(id=response.ids[0])
