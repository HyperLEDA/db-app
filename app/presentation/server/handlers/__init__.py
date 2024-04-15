from app.presentation.server.handlers.create_object import create_object_handler
from app.presentation.server.handlers.create_objects import create_objects_handler
from app.presentation.server.handlers.create_source import create_source_handler
from app.presentation.server.handlers.debug_start_task import debug_start_task_handler
from app.presentation.server.handlers.get_object_names import get_object_names_handler
from app.presentation.server.handlers.get_source import get_source_handler
from app.presentation.server.handlers.get_source_list import get_source_list_handler
from app.presentation.server.handlers.get_task_info import get_task_info_handler
from app.presentation.server.handlers.ping import ping_handler
from app.presentation.server.handlers.search_catalogs import search_catalogs_handler
from app.presentation.server.handlers.start_task import start_task_handler

__all__ = [
    "create_object_handler",
    "create_objects_handler",
    "create_source_handler",
    "get_object_names_handler",
    "get_source_handler",
    "get_source_list_handler",
    "ping_handler",
    "search_catalogs_handler",
    "start_task_handler",
    "get_task_info_handler",
    "debug_start_task_handler",
]
