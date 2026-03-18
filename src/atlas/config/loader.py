"""Configuration loading from YAML files with environment variable interpolation."""
from __future__ import annotations

import os
import re
from pathlib import Path
from typing import Any

import yaml
from dotenv import load_dotenv

from atlas.config.models import AtlasConfig
from atlas.core.errors import AtlasConfigError

# Load .env file once at import time so ${ENV_VAR} references resolve automatically
load_dotenv()

# Pattern for ${ENV_VAR} or ${ENV_VAR:default}
ENV_VAR_PATTERN = re.compile(r"\$\{([^}:]+)(?::([^}]*))?\}")

DEFAULT_CONFIG_PATHS = [
    Path("atlas.yaml"),
    Path("atlas.yml"),
    Path(".atlas/config.yaml"),
    Path(".atlas/config.yml"),
]


def _interpolate_env_vars(value: Any) -> Any:
    """Recursively interpolate ${ENV_VAR} and ${ENV_VAR:default} patterns."""
    if isinstance(value, str):
        def replacer(match):
            var_name = match.group(1)
            default = match.group(2)
            env_val = os.environ.get(var_name)
            if env_val is not None:
                return env_val
            if default is not None:
                return default
            raise AtlasConfigError(
                f"Environment variable '{var_name}' not set and no default provided",
                field_name=var_name,
            )
        return ENV_VAR_PATTERN.sub(replacer, value)
    elif isinstance(value, dict):
        return {k: _interpolate_env_vars(v) for k, v in value.items()}
    elif isinstance(value, list):
        return [_interpolate_env_vars(item) for item in value]
    return value


def load_yaml_file(path: Path) -> dict[str, Any]:
    """Load and parse a YAML file with env var interpolation."""
    if not path.exists():
        raise AtlasConfigError(f"Config file not found: {path}", field_name="config_file")

    try:
        with open(path) as f:
            raw = yaml.safe_load(f) or {}
    except yaml.YAMLError as e:
        raise AtlasConfigError(f"Invalid YAML in {path}: {e}", field_name="config_file") from e

    return _interpolate_env_vars(raw)


def find_config_file(explicit_path: Path | None = None) -> Path | None:
    """Find config file: explicit path > ATLAS_CONFIG env > default locations."""
    if explicit_path:
        if explicit_path.exists():
            return explicit_path
        raise AtlasConfigError(f"Config file not found: {explicit_path}", field_name="config_file")

    env_path = os.environ.get("ATLAS_CONFIG")
    if env_path:
        p = Path(env_path)
        if p.exists():
            return p
        raise AtlasConfigError(f"Config file from ATLAS_CONFIG not found: {p}", field_name="config_file")

    for default in DEFAULT_CONFIG_PATHS:
        if default.exists():
            return default

    return None


def load_config(config_path: Path | None = None) -> AtlasConfig:
    """Load ATLAS configuration from YAML file or defaults.

    Args:
        config_path: Explicit path to config file. If None, searches default locations.

    Returns:
        AtlasConfig instance with validated configuration.
    """
    path = find_config_file(config_path)

    if path is None:
        return AtlasConfig()

    raw = load_yaml_file(path)

    try:
        return AtlasConfig.model_validate(raw)
    except Exception as e:
        raise AtlasConfigError(f"Invalid configuration: {e}", field_name="config") from e
