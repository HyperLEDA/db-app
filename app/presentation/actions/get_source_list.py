from app.domain.model import (
    GetSourceListRequest,
    GetSourceListResponse,
    GetSourceResponse,
)


def get_source_list(r: GetSourceListRequest) -> GetSourceListResponse:
    return GetSourceListResponse(
        [
            GetSourceResponse("paper", {"bibcode": "12345678"}),
            GetSourceResponse("table", {"name": "test table"}),
        ]
    )
