"""
配置管理模块
负责读取和写入 config.yaml 配置文件
"""
import os
import yaml

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
CONFIG_PATH = os.path.join(ROOT_DIR, "config.yaml")
DATA_DIR = os.path.join(ROOT_DIR, "data")


class Settings:
    """全局配置管理器"""

    def __init__(self):
        self._config = {}
        self.load()

    def load(self):
        if os.path.exists(CONFIG_PATH):
            with open(CONFIG_PATH, "r", encoding="utf-8") as f:
                self._config = yaml.safe_load(f) or {}
        os.makedirs(DATA_DIR, exist_ok=True)

    def save(self):
        with open(CONFIG_PATH, "w", encoding="utf-8") as f:
            yaml.dump(self._config, f, allow_unicode=True, default_flow_style=False)

    def get(self, key: str, default=None):
        keys = key.split(".")
        value = self._config
        for k in keys:
            if isinstance(value, dict):
                value = value.get(k)
            else:
                return default
        return value if value is not None else default

    def set(self, key: str, value):
        keys = key.split(".")
        target = self._config
        for k in keys[:-1]:
            if k not in target:
                target[k] = {}
            target = target[k]
        target[keys[-1]] = value
        self.save()

    @property
    def language(self) -> str:
        return self.get("language", "zh")

    @language.setter
    def language(self, value: str):
        self.set("language", value)

    @property
    def engine_defaults(self) -> dict:
        return self.get("engine_defaults", {})

    @property
    def default_roles(self) -> dict:
        return self.get("default_roles", {})


# 全局单例
settings = Settings()
