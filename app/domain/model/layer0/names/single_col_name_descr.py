from app.domain.model.layer0.names.multi_col_name_descr import MultyColNameDescr


class SingleColNameDescr(MultyColNameDescr):
    """Case, when object has single name"""

    def __init__(self, column_name):
        super().__init__(column_name, [column_name])
