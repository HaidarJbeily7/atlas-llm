"""Tests for configuration."""
import os
import pytest
from atlas.config.models import AtlasConfig, ProviderConfig
from atlas.config.loader import _interpolate_env_vars, load_config
from atlas.config.profiles import get_profile, BUILTIN_PROFILES
from atlas.core.errors import AtlasConfigError


class TestAtlasConfig:
    def test_default_config(self):
        config = AtlasConfig()
        assert config.provider.model == "openai/gpt-4o"
        assert config.scan.concurrency == 10

    def test_provider_config(self):
        p = ProviderConfig(model="anthropic/claude-3-opus", timeout=60)
        assert p.model == "anthropic/claude-3-opus"
        assert p.timeout == 60


class TestEnvInterpolation:
    def test_simple_var(self, monkeypatch):
        monkeypatch.setenv("TEST_VAR", "hello")
        result = _interpolate_env_vars("${TEST_VAR}")
        assert result == "hello"

    def test_default_value(self):
        result = _interpolate_env_vars("${NONEXISTENT_VAR:default_val}")
        assert result == "default_val"

    def test_missing_var_raises(self):
        with pytest.raises(AtlasConfigError):
            _interpolate_env_vars("${DEFINITELY_MISSING}")

    def test_nested_dict(self, monkeypatch):
        monkeypatch.setenv("MY_KEY", "secret")
        result = _interpolate_env_vars({"api_key": "${MY_KEY}", "other": "plain"})
        assert result == {"api_key": "secret", "other": "plain"}


class TestProfiles:
    def test_builtin_profiles_exist(self):
        assert "quick" in BUILTIN_PROFILES
        assert "standard" in BUILTIN_PROFILES
        assert "full" in BUILTIN_PROFILES

    def test_get_profile(self):
        p = get_profile("quick")
        assert p.name == "quick"
        assert len(p.probes) > 0

    def test_unknown_profile_raises(self):
        with pytest.raises(ValueError):
            get_profile("nonexistent")


class TestLoadConfig:
    def test_default_when_no_file(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        config = load_config()
        assert isinstance(config, AtlasConfig)
