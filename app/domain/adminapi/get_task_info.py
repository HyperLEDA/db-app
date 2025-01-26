from app import schema
from app.commands.adminapi import depot


def get_task_info(dpt: depot.Depot, r: schema.GetTaskInfoRequest) -> schema.GetTaskInfoResponse:
    task_info = dpt.common_repo.get_task_info(r.task_id)
    return schema.GetTaskInfoResponse(
        task_info.id,
        task_info.task_name,
        str(task_info.status.value),
        task_info.payload,
        task_info.start_time,
        task_info.end_time,
        task_info.message,
    )
