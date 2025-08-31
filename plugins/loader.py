import importlib.util
from pathlib import Path
from typing import Any

from app.domain.unification.crossmatch import CIMatcher, CISolver


class PluginLoader:
    def __init__(self):
        self.matchers: dict[str, CIMatcher] = {}
        self.solvers: dict[str, CISolver] = {}
        self._load_plugins()

    def _load_plugins(self):
        plugins_dir = Path(__file__).parent

        matchers_dir = plugins_dir / "matchers"
        if matchers_dir.exists():
            self._load_plugins_from_directory(matchers_dir, self.matchers, "matcher")

        solvers_dir = plugins_dir / "solvers"
        if solvers_dir.exists():
            self._load_plugins_from_directory(solvers_dir, self.solvers, "solver")

    def _load_plugins_from_directory(self, directory: Path, target_dict: dict[str, Any], plugin_type: str):
        for py_file in directory.glob("*.py"):
            if py_file.name == "__init__.py":
                continue

            try:
                spec = importlib.util.spec_from_file_location(py_file.stem, py_file)
                if spec is None or spec.loader is None:
                    continue

                module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(module)

                if not hasattr(module, "name"):
                    print(f"Warning: Plugin {py_file} missing 'name' variable")
                    continue

                if not hasattr(module, "plugin"):
                    print(f"Warning: Plugin {py_file} missing 'plugin' variable")
                    continue

                plugin_name = module.name
                plugin_func = module.plugin

                if not callable(plugin_func):
                    print(f"Warning: Plugin {py_file} plugin is not callable")
                    continue

                target_dict[plugin_name] = plugin_func
            except Exception as e:
                print(f"Warning: Failed to load plugin {py_file}: {e}")

    def get_matcher(self, name: str) -> CIMatcher:
        if name not in self.matchers:
            raise ValueError(f"Unknown matcher: {name}")
        return self.matchers[name]

    def get_solver(self, name: str) -> CISolver:
        if name not in self.solvers:
            raise ValueError(f"Unknown solver: {name}")
        return self.solvers[name]

    def list_matchers(self) -> list[str]:
        return list(self.matchers.keys())

    def list_solvers(self) -> list[str]:
        return list(self.solvers.keys())


plugin_loader = PluginLoader()
