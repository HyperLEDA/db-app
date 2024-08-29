from app import commands, schema

ALLOWED_CHARS = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_"


def construct_code(authors: list[str], year: int, title: str) -> str:
    author_part = authors[0].split()[0]
    title_part = "_".join(title.split()[:3])

    code = f"{year}_{author_part}_{title_part}"
    code.replace(" ", "_")

    return "".join([c for c in code if c in ALLOWED_CHARS])


def create_source(depot: commands.Depot, r: schema.CreateSourceRequest) -> schema.CreateSourceResponse:
    code = construct_code(r.authors, r.year, r.title)
    _ = depot.common_repo.create_bibliography(code, r.year, r.authors, r.title)

    return schema.CreateSourceResponse(code=code)
