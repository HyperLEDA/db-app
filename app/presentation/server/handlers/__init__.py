from app.presentation.server.handlers import (
    add_data,
    create_source,
    create_table,
    debug_start_task,
    get_source,
    get_source_list,
    get_task_info,
    ping,
    search_catalogs,
    start_task,
)

routes = [
    ping.description,
    create_source.description,
    get_source_list.description,
    get_source.description,
    search_catalogs.description,
    start_task.description,
    debug_start_task.description,
    get_task_info.description,
    create_table.description,
    add_data.description,
]
