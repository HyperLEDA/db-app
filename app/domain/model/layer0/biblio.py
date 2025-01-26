from dataclasses import dataclass


@dataclass
class Biblio:
    """
    Holds bibliographic information
    Args:
        id: Unique bibliography id
        ref_str: A code, used to find an article on [https://ui.adsabs.harvard.edu/]
        first_author: First author
        year: Publish year
    """

    id: int | None
    ref_str: str | None
    authors: list[str]
    year: int
    title: str
