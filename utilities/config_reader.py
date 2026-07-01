import json
import os
from functools import lru_cache


class ConfigReader:
    """Loads global config and environment-specific overrides."""

    _ROOT = os.path.dirname(os.path.dirname(__file__))
    _CONFIG_DIR = os.path.join(_ROOT, "config")

    @classmethod
    @lru_cache(maxsize=1)
    def _load_global(cls):
        path = os.path.join(cls._CONFIG_DIR, "config.json")
        with open(path, encoding="utf-8") as handle:
            return json.load(handle)

    @classmethod
    def get_environment_name(cls):
        return os.getenv("TEST_ENV", cls._load_global().get("default_environment", "prod"))

    @classmethod
    @lru_cache(maxsize=4)
    def _load_environment(cls, env_name):
        path = os.path.join(cls._CONFIG_DIR, "environments", f"{env_name}.json")
        if not os.path.exists(path):
            raise FileNotFoundError(f"Environment config not found: {path}")
        with open(path, encoding="utf-8") as handle:
            return json.load(handle)

    @classmethod
    def get_environment(cls):
        return cls._load_environment(cls.get_environment_name())

    @classmethod
    def get(cls, key, default=None):
        env_config = cls.get_environment()
        global_config = cls._load_global()
        if key in env_config:
            return env_config[key]
        return global_config.get(key, default)

    @classmethod
    def get_path(cls, key, default=None):
        relative = cls.get(key, default)
        if not relative:
            return None
        return os.path.join(cls._ROOT, relative)

    @classmethod
    def get_all(cls):
        merged = cls._load_global().copy()
        merged.update(cls.get_environment())
        merged["environment"] = cls.get_environment_name()
        return merged

    @classmethod
    def reset_cache(cls):
        cls._load_global.cache_clear()
        cls._load_environment.cache_clear()
