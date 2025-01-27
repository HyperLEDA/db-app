from app.data import repositories
from app.presentation import adminapi

ALLOWED_CHARS = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_"


def construct_code(authors: list[str], year: int, title: str) -> str:
    author_part = authors[0].split()[0]
    title_part = "_".join(title.split()[:3])

    code = f"{year}_{author_part}_{title_part}"
    code.replace(" ", "_")

    return "".join([c for c in code if c in ALLOWED_CHARS])


class SourceManager:
    def __init__(self, common_repo: repositories.CommonRepository):
        self.common_repo = common_repo

    def create_source(self, r: adminapi.CreateSourceRequest) -> adminapi.CreateSourceResponse:
        code = construct_code(r.authors, r.year, r.title)
        _ = self.common_repo.create_bibliography(code, r.year, r.authors, r.title)

        return adminapi.CreateSourceResponse(code=code)

    def get_source(self, r: adminapi.GetSourceRequest) -> adminapi.GetSourceResponse:
        result = self.common_repo.get_source_by_id(r.id)

        return adminapi.GetSourceResponse(
            result.code,
            result.title,
            result.author,
            result.year,
        )
