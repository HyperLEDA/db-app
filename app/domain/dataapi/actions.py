from app.data import repositories
from app.presentation import dataapi


class Actions(dataapi.Actions):
    def __init__(self, layer2_repo: repositories.Layer2Repository) -> None:
        self.layer2_repo = layer2_repo

    def query_simple(self, query: dataapi.QuerySimpleRequest) -> dataapi.QuerySimpleResponse:
        return dataapi.QuerySimpleResponse([])

    def get_object(self, query: dataapi.GetObjectRequest) -> dataapi.GetObjectResponse:
        return dataapi.GetObjectResponse(dataapi.PGCObject(123, {}))
