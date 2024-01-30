from dataclasses import dataclass
from typing import Optional


@dataclass
class Biblio:
    """
    Holds bibliographic information
    Args:
        ref_str: A code, used to find an article on [https://ui.adsabs.harvard.edu/]
        first_author: First author
        year: Publish year
    """
    ref_str: Optional[str]
    first_author: Optional[str]
    year: Optional[int]
