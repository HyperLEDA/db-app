from presentation import actions
from presentation.server.exceptions.apiexception import new_internal_error
from presentation.model import CreateObjectRequest, CreateObjectResponse, CreateObjectBatchRequest


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
