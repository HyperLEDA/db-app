from app.data import repositories
from app.presentation import adminapi


class TableTransferManager:
    def __init__(
        self,
        common_repo: repositories.CommonRepository,
        layer0_repo: repositories.Layer0Repository,
        layer1_repo: repositories.Layer1Repository,
        layer2_repo: repositories.Layer2Repository,
    ) -> None:
        self.common_repo = common_repo
        self.layer0_repo = layer0_repo
        self.layer1_repo = layer1_repo
        self.layer2_repo = layer2_repo

    def table_status_stats(self, r: adminapi.TableStatusStatsRequest) -> adminapi.TableStatusStatsResponse:
        stats = self.layer0_repo.get_table_statistics(r.table_id)

        return adminapi.TableStatusStatsResponse(processing=stats.statuses)
