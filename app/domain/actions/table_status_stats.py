from app import commands, schema


def table_status_stats(depot: commands.Depot, r: schema.TableStatusStatsRequest) -> schema.TableStatusStatsResponse:
    return schema.TableStatusStatsResponse(processing=depot.layer0_repo.get_object_statuses(r.table_id))
