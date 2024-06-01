import pandas

from app import commands
from app.data import model as data_model
from app.domain import model as domain_model


def add_data(depot: commands.Depot, r: domain_model.AddDataRequest) -> domain_model.AddDataResponse:
    data_df = pandas.DataFrame.from_records(r.data)

    with depot.layer0_repo.with_tx() as tx:
        depot.layer0_repo.insert_raw_data(
            data_model.Layer0RawData(
                table_id=r.table_id,
                data=data_df,
            ),
            tx=tx,
        )

    return domain_model.AddDataResponse()
