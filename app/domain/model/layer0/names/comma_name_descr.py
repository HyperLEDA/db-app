from pandas import Series

from app.domain.model.layer0.names.name_descr import NameDescr


class CommaNameDescr(NameDescr):
    """Case, where different names come in single column, comma separated"""

    def __init__(self, name_col: str, main_idx: int):
        self._name_col = name_col
        self._main_idx = main_idx

    def _parse_row(self, data: Series) -> tuple[str, list[str]]:
        names = data[self._name_col].split(",")

        return names[self._main_idx], names
