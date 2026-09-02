"""配置读写：当前任务模式（日常 / 周常）。"""
import json
import os

from . import logger

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CONFIG_DIR = os.path.join(BASE_DIR, "config")
SETTINGS_PATH = os.path.join(CONFIG_DIR, "settings.json")

# 模式键 -> 中文名
TASK_MODES = {"daily": "日常", "weekly": "周常"}
DEFAULT_MODE = "weekly"
DEFAULTS = {"task_mode": DEFAULT_MODE}


def load_settings():
    """读取设置，缺失字段用默认值补齐。"""
    settings = dict(DEFAULTS)
    if os.path.exists(SETTINGS_PATH):
        try:
            with open(SETTINGS_PATH, encoding="utf-8") as f:
                data = json.load(f)
            for key in DEFAULTS:
                if key in data:
                    settings[key] = data[key]
        except (OSError, ValueError) as e:
            logger.error(f"读取设置失败，使用默认值。{e}")
    return settings


def save_settings(settings):
    """写回设置。"""
    os.makedirs(CONFIG_DIR, exist_ok=True)
    with open(SETTINGS_PATH, "w", encoding="utf-8") as f:
        json.dump(settings, f, ensure_ascii=False, indent=2)


def mode_label(mode):
    """返回模式的中文名，未知模式原样返回。"""
    return TASK_MODES.get(mode, mode)
