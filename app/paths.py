"""路径工具：区分源码运行与打包（PyInstaller）运行。"""
import os
import sys


def resource_dir():
    """资源目录：打包后为解包目录（_MEIPASS），源码运行为项目根目录。"""
    if getattr(sys, "frozen", False):
        return sys._MEIPASS
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def app_dir():
    """应用数据目录：打包后为 exe 所在目录（用户可改），源码运行为项目根目录。"""
    if getattr(sys, "frozen", False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
