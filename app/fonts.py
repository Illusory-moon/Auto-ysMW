"""字体加载：优先使用项目内置的原神字体（resource/font），失败则回退系统字体。"""
import os

from PyQt5.QtGui import QFont, QFontDatabase
from PyQt5.QtWidgets import QApplication

from .paths import resource_dir

FONT_DIR = os.path.join(resource_dir(), "resource", "font")

# 兜底字体（项目内没有自定义字体时的回退）
_FALLBACKS = ["Microsoft YaHei", "SimHei", "Microsoft YaHei UI", "Segoe UI", "Arial"]


def _first_loaded_family():
    """加载 resource/font 下的字体，返回第一个字体族名。"""
    database = QFontDatabase()
    if not os.path.isdir(FONT_DIR):
        return None
    for name in os.listdir(FONT_DIR):
        if not name.lower().endswith((".ttf", ".otf", ".ttc")):
            continue
        path = os.path.join(FONT_DIR, name)
        font_id = database.addApplicationFont(path)
        if font_id == -1:
            continue
        families = database.applicationFontFamilies(font_id)
        if families:
            return families[0]
    return None


def apply_default_font() -> str:
    """把字体设为应用默认字体，返回实际使用的字体族名。"""
    family = _first_loaded_family() or _FALLBACKS[0]
    app = QApplication.instance()
    app.setFont(QFont(family, 11))
    return family
