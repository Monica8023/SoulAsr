"""Engine adapters package."""

from importlib import import_module
from pkgutil import iter_modules

from backend.src.engines.base_engine import BaseEngine


def discover_engines() -> dict[str, type[BaseEngine]]:
    for module_info in iter_modules(__path__):
        if module_info.name.endswith("_engine") and module_info.name != "base_engine":
            import_module(f"{__name__}.{module_info.name}")
    return BaseEngine.get_registry()
