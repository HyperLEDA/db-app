from app import commands
from app.domain import model as domain_model


def get_task_info(depot: commands.Depot, r: domain_model.GetTaskInfoRequest) -> domain_model.GetTaskInfoResponse:
    task_info = depot.common_repo.get_task_info(r.task_id)
    return domain_model.GetTaskInfoResponse(
        task_info.id,
        task_info.task_name,
        str(task_info.status.value),
        task_info.payload,
        task_info.start_time,
        task_info.end_time,
        task_info.message,
    )
