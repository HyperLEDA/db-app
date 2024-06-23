from app import commands
from app.data import model as data_model
from app.domain import model as domain_model
from app.lib.exceptions import new_validation_error
from app.lib.storage import enums, mapping


def create_table(depot: commands.Depot, r: domain_model.CreateTableRequest) -> domain_model.CreateTableResponse:
    columns = []

    for col in r.columns:
        try:
            col_type = mapping.get_type(col.data_type)
        except ValueError as e:
            raise new_validation_error(str(e)) from e

        columns.append(
            data_model.ColumnDescription(name=col.name, data_type=col_type, unit=col.unit, description=col.description)
        )

    with depot.layer0_repo.with_tx() as tx:
        table_id = depot.layer0_repo.create_table(
            data_model.Layer0Creation(
                table_name=r.table_name,
                column_descriptions=columns,
                bibliography_id=r.bibliography_id,
                datatype=enums.DataType(r.datatype),
                comment=r.description,
            ),
            tx=tx,
        )

    return domain_model.CreateTableResponse(table_id)
