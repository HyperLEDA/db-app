import pytest

from app.adminapi.domain.sources import construct_code


@pytest.mark.parametrize(
    "authors,year,title,code",
    [
        (["Hawking J."], 2021, "Title", "2021_Hawking_Title"),
        (["Newton I.", "Einstein A."], 1650, "Theory of gravitation", "1650_Newton_Theory_of_gravitation"),
        (["Galilei G.", "Kepler J."], 1600, "Long title of the book", "1600_Galilei_Long_title_of"),
    ],
)
def test_construct_code(authors: list[str], year: int, title: str, code: str) -> None:
    assert construct_code(authors, year, title) == code
