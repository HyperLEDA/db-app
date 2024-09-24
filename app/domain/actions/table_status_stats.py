from app import commands, schema
from app.lib.storage import enums


def table_status_stats(depot: commands.Depot, r: schema.TableStatusStatsRequest) -> schema.TableStatusStatsResponse:
    return schema.TableStatusStatsResponse(
        processing={
            enums.ObjectProcessingStatus.NEW: 1,
            enums.ObjectProcessingStatus.EXISTING: 2,
            enums.ObjectProcessingStatus.UNPROCESSED: 3,
            enums.ObjectProcessingStatus.COLLIDED: 4,
        }
    )
