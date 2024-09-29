from app.presentation.server.handlers import (
    add_data,
    create_source,
    create_table,
    get_source,
    get_task_info,
    login,
    ping,
    start_task,
    table_process,
    table_status_stats,
)

routes = [
    ping.description,
    create_source.description,
    get_source.description,
    start_task.description,
    get_task_info.description,
    create_table.description,
    add_data.description,
    login.description,
    table_process.description,
    table_status_stats.description,
]
