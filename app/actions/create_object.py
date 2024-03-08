from app import actions
from app.server.exceptions.apiexception import new_internal_error
from app.server.schema import CreateObjectRequest, CreateObjectResponse
from app.server.schema.object import CreateObjectBatchRequest


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
