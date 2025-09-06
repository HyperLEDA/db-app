import importlib.util
import sys
from collections.abc import Callable
from pathlib import Path
from typing import cast

import structlog

from app.domain.unification.crossmatch import CIMatcher, CISolver

logger: structlog.stdlib.BoundLogger = structlog.get_logger()

PluginType = Callable[..., CIMatcher] | Callable[..., CISolver]


def _discover_plugins_generic(directory: str) -> dict[str, PluginType]:
    plugins: dict[str, PluginType] = {}

    py_files = Path(directory).glob("*.py")

    for file_path in py_files:
        module_name = file_path.stem
        spec = importlib.util.spec_from_file_location(module_name, str(file_path))
        if spec is None or spec.loader is None:
            continue

        module = importlib.util.module_from_spec(spec)
        sys.modules[module_name] = module
        spec.loader.exec_module(module)

        if not hasattr(module, "plugin"):
            logger.warn("python file has no declared plugin", filename=str(file_path))
            continue

        plugin = module.plugin

        if not hasattr(module, "name"):
            logger.warn(
                "python file has no declared plugin name",
                filename=str(file_path),
                plugin=plugin.__name__,
            )
            continue

        plugin_name = module.name
        plugins[plugin_name] = plugin

        logger.info("discovered plugin", name=plugin_name)

    return plugins


def discover_matchers(directory: str) -> dict[str, Callable[..., CIMatcher]]:
    plugins = _discover_plugins_generic(directory)
    return cast(dict[str, Callable[..., CIMatcher]], plugins)


def discover_solvers(directory: str) -> dict[str, Callable[..., CISolver]]:
    plugins = _discover_plugins_generic(directory)
    return cast(dict[str, Callable[..., CISolver]], plugins)
