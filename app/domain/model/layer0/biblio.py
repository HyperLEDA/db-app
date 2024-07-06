from dataclasses import dataclass
from typing import Optional


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

    id: Optional[int]
    ref_str: Optional[str]
    authors: list[str]
    year: int
    title: str
