from app import schema
from app.commands.adminapi import depot


def table_status_stats(dpt: depot.Depot, r: schema.TableStatusStatsRequest) -> schema.TableStatusStatsResponse:
    return schema.TableStatusStatsResponse(processing=dpt.layer0_repo.get_object_statuses(r.table_id))
