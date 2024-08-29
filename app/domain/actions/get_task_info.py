from app import commands, schema


def get_task_info(depot: commands.Depot, r: schema.GetTaskInfoRequest) -> schema.GetTaskInfoResponse:
    task_info = depot.common_repo.get_task_info(r.task_id)
    return schema.GetTaskInfoResponse(
        task_info.id,
        task_info.task_name,
        str(task_info.status.value),
        task_info.payload,
        task_info.start_time,
        task_info.end_time,
        task_info.message,
    )
