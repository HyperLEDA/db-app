from astropy import table

from app.domain.unification.modifiers import interface


class Applicator:
    def __init__(self) -> None:
        self._modifiers: dict[str, list[interface.ColumnModifier]] = {}

    def add_modifier(self, column_name: str, modifier: interface.ColumnModifier):
        if column_name not in self._modifiers:
            self._modifiers[column_name] = []
        self._modifiers[column_name].append(modifier)

    def apply(self, data: table.Table) -> table.Table:
        result = data.copy()

        for column_name, modifiers in self._modifiers.items():
            if column_name not in result.colnames:
                continue

            column_data: table.Column = result[column_name]  # type: ignore

            for modifier in modifiers:
                column_data = modifier.apply(column_data)  # type: ignore

            result[column_name] = column_data

        return result
