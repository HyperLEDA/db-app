import psycopg
from astropy import units as u

from app.data import model
from app.data.repositories import layer1
from app.lib.web.errors import RuleValidationError
from app.presentation import adminapi


class Layer1Writer:
    def __init__(self, layer1_repo: layer1.Layer1Repository) -> None:
        self._layer1_repo = layer1_repo

    def save_data(self, request: adminapi.SaveStructuredDataRequest) -> adminapi.SaveStructuredDataResponse:
        catalog = model.RawCatalog(request.catalog)
        object_cls = model.get_catalog_object_type(catalog)
        table = object_cls.layer1_table()

        internal_units = self._layer1_repo.get_column_units(catalog)
        missing = [col for col in request.columns if col in internal_units and col not in request.units]
        if missing:
            raise RuleValidationError(f"units required for columns: {', '.join(sorted(missing))}")

        factors: list[float | None] = [None] * len(request.columns)
        for j, col in enumerate(request.columns):
            if col in internal_units and col in request.units:
                factors[j] = (1.0 * u.Unit(request.units[col])).to(u.Unit(internal_units[col])).value
            else:
                factors[j] = None

        converted = []
        for row in request.data:
            new_row = []
            for value, factor in zip(row, factors, strict=True):
                if factor is not None:
                    new_row.append(float(value) * factor)
                else:
                    new_row.append(value)
            converted.append(new_row)

        try:
            conflict_keys = object_cls.layer1_primary_keys()
            self._layer1_repo.save_structured_data(
                table, request.columns, request.ids, converted, conflict_keys=conflict_keys
            )
        except psycopg.errors.ForeignKeyViolation as e:
            diag = getattr(e, "diag", None)
            detail = getattr(diag, "message_detail", None) if diag else None
            constraint = getattr(diag, "constraint_name", None) if diag else None
            msg = "foreign key violation"
            if constraint:
                msg += f": {constraint}"
            if detail:
                msg += f" ({detail})"
            raise RuleValidationError(msg) from e

        return adminapi.SaveStructuredDataResponse()
