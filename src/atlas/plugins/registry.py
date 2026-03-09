"""Plugin discovery and registration for ATLAS."""
from __future__ import annotations

import importlib
import importlib.metadata
from typing import Any, TypeVar

from atlas.core.errors import PluginError
from atlas.logging.setup import get_logger

logger = get_logger(__name__)

T = TypeVar("T")

# Global registries by plugin type
_REGISTRIES: dict[str, dict[str, type]] = {
    "probes": {},
    "detectors": {},
    "generators": {},
    "evaluators": {},
    "reporters": {},
}


def register(plugin_type: str, name: str | None = None):
    """Decorator to register a plugin class.

    Args:
        plugin_type: One of 'probes', 'detectors', 'generators', 'evaluators', 'reporters'
        name: Optional name override; defaults to class name

    Usage:
        @register("probes")
        class MyProbe(BaseProbe):
            ...

        @register("detectors", name="custom_keyword")
        class MyDetector(BaseDetector):
            ...
    """
    if plugin_type not in _REGISTRIES:
        raise PluginError(f"Unknown plugin type: {plugin_type}. Must be one of {list(_REGISTRIES)}")

    def decorator(cls: type[T]) -> type[T]:
        plugin_name = name or cls.__name__
        _REGISTRIES[plugin_type][plugin_name] = cls
        logger.debug("registered_plugin", plugin_type=plugin_type, name=plugin_name)
        return cls

    return decorator


def get_plugin(plugin_type: str, name: str) -> type:
    """Get a registered plugin class by type and name."""
    if plugin_type not in _REGISTRIES:
        raise PluginError(f"Unknown plugin type: {plugin_type}")

    registry = _REGISTRIES[plugin_type]
    if name not in registry:
        available = list(registry.keys())
        raise PluginError(
            f"Plugin '{name}' not found in {plugin_type}. Available: {available}"
        )
    return registry[name]


def list_plugins(plugin_type: str | None = None) -> dict[str, list[str]]:
    """List registered plugins, optionally filtered by type."""
    if plugin_type:
        if plugin_type not in _REGISTRIES:
            raise PluginError(f"Unknown plugin type: {plugin_type}")
        return {plugin_type: list(_REGISTRIES[plugin_type].keys())}
    return {k: list(v.keys()) for k, v in _REGISTRIES.items()}


def discover_entrypoints(group: str = "atlas.plugins") -> None:
    """Discover plugins from installed packages via entry_points."""
    try:
        eps = importlib.metadata.entry_points()
        # Python 3.12+ returns a SelectableGroups, 3.9+ returns dict
        if hasattr(eps, "select"):
            entries = eps.select(group=group)
        else:
            entries = eps.get(group, [])

        for ep in entries:
            try:
                ep.load()
                logger.debug("loaded_entrypoint", name=ep.name, group=group)
            except Exception as e:
                logger.warning("entrypoint_load_failed", name=ep.name, error=str(e))
    except Exception as e:
        logger.warning("entrypoint_discovery_failed", error=str(e))


def import_module_plugins(module_path: str) -> None:
    """Import a module to trigger @register decorators."""
    try:
        importlib.import_module(module_path)
    except ImportError as e:
        raise PluginError(f"Failed to import plugin module: {module_path}: {e}") from e


def discover_builtin_plugins() -> None:
    """Import all built-in ATLAS plugin modules to trigger registration."""
    builtin_modules = [
        "atlas.probes.prompt_injection",
        "atlas.probes.jailbreak",
        "atlas.probes.encoding",
        "atlas.probes.extraction",
        "atlas.probes.toxicity",
        "atlas.probes.hallucination",
        "atlas.probes.web_injection",
        "atlas.probes.malware",
        "atlas.probes.agent_harm",
        "atlas.detectors.keyword",
        "atlas.detectors.refusal",
        "atlas.detectors.llm_judge",
        "atlas.generators.litellm",
    ]
    for mod in builtin_modules:
        try:
            importlib.import_module(mod)
        except ImportError:
            logger.debug("builtin_module_not_found", module=mod)


def clear_registry(plugin_type: str | None = None) -> None:
    """Clear registries. Mainly for testing."""
    if plugin_type:
        _REGISTRIES[plugin_type].clear()
    else:
        for reg in _REGISTRIES.values():
            reg.clear()
