from presentation.model import (
    CreateObjectBatchRequest,
    CreateObjectBatchResponse,
)


def create_objects(r: CreateObjectBatchRequest) -> CreateObjectBatchResponse:
    results = []

    for i in range(len(r.objects)):
        results.append(i)

    return CreateObjectBatchResponse(ids=results)
