from pandas import Series

from app.domain.model.layer0.names.name_descr import NameDescr


class MultyColNameDescr(NameDescr):
    """Case, where different names go in different columns"""

    def __init__(self, main_col, name_cols):
        """
        :param main_col: Column, where main name is located
        :param name_cols: Columns, containing names
        """
        self._main_col = main_col
        self._name_cols = name_cols

    def _parse_row(self, data: Series) -> tuple[str, list[str]]:
        main_name = data[self._main_col]
        all_names = data[self._name_cols]

        return main_name, list(all_names)
