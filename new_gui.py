"""千星奇域助手主界面：左侧日志、右侧操作按钮、顶部标签页（控制台 / 设置）。

作为入口脚本直接运行：uv run new_gui.py
"""
import ctypes
import os
import sys
import threading

from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QKeySequence
from PyQt5.QtWidgets import (
    QApplication,
    QComboBox,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QPushButton,
    QShortcut,
    QTabWidget,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from app import config, fonts, logger
from app.focus import focus_genshin, game_client_rect
from app.hotkey import register as register_hotkeys
from app.ocr import scan_text
from app.task import TaskRunner

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
STYLE_PATH = os.path.join(BASE_DIR, "resource", "theme", "style.qss")


class MainWindow(QMainWindow):
    _hotkey = pyqtSignal(str)  # action: "stop" / "print"
    _log_line = pyqtSignal(str)
    _task_finished = pyqtSignal()

    def __init__(self):
        super().__init__()
        self.setWindowTitle("千星奇域助手")
        self.resize(960, 620)

        self.settings = config.load_settings()
        self.runner = TaskRunner(on_finish=self._task_finished.emit)

        self._build_ui()
        self._connect()
        logger.setup(self._on_log)
        self._setup_hotkeys()

        self._refresh_mode_text()
        logger.info("千星奇域助手已启动")

    # ------------------------------------------------------------------ UI
    def _build_ui(self):
        self.tabs = QTabWidget()
        self.setCentralWidget(self.tabs)

        self.tabs.addTab(self._build_console_tab(), "控制台")
        self.tabs.addTab(self._build_settings_tab(), "千星奇域设置")

    def _build_console_tab(self):
        page = QWidget()
        root = QVBoxLayout(page)

        # 顶部状态行
        top = QHBoxLayout()
        self.status_label = QLabel("任务：未运行")
        self.status_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        top.addStretch(1)
        top.addWidget(self.status_label)
        root.addLayout(top)

        # 主体：左日志 | 右按钮
        body = QHBoxLayout()
        self.log_view = QTextEdit()
        self.log_view.setReadOnly(True)
        self.log_view.setMinimumWidth(420)
        body.addWidget(self.log_view, 4)

        right = QVBoxLayout()
        right.setSpacing(12)
        right.addStretch(1)

        self.start_btn = QPushButton("开始千星奇域周常")
        self.stop_btn = QPushButton("F5 停止任务")
        self.print_btn = QPushButton("F7 打印屏幕上的文本坐标")
        self.clear_btn = QPushButton("清空日志")

        for btn in (self.start_btn, self.stop_btn, self.print_btn, self.clear_btn):
            btn.setFixedHeight(36)

        right.addWidget(self.start_btn)
        right.addWidget(self.stop_btn)
        right.addWidget(self.print_btn)
        right.addWidget(self.clear_btn)
        right.addStretch(1)

        body.addLayout(right, 1)
        root.addLayout(body, 1)
        return page

    def _build_settings_tab(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setSpacing(12)
        layout.addStretch(1)

        layout.addWidget(QLabel("任务模式"))

        self.mode_combo = QComboBox()
        for key, label in config.TASK_MODES.items():
            self.mode_combo.addItem(label, key)
        idx = self.mode_combo.findData(self.settings["task_mode"])
        if idx >= 0:
            self.mode_combo.setCurrentIndex(idx)
        self.mode_combo.setMinimumWidth(220)
        layout.addWidget(self.mode_combo)

        self.settings_save_btn = QPushButton("保存")
        self.settings_save_btn.setMinimumHeight(34)
        layout.addWidget(self.settings_save_btn)

        layout.addStretch(1)
        return page

    def _connect(self):
        self.start_btn.clicked.connect(self.start_task)
        self.stop_btn.clicked.connect(self.stop_task)
        self.print_btn.clicked.connect(self.print_text_coords)
        self.clear_btn.clicked.connect(self.clear_logs)
        self.settings_save_btn.clicked.connect(self.save_settings)
        self._hotkey.connect(self._handle_hotkey, Qt.QueuedConnection)
        self._log_line.connect(self._append_log)
        self._task_finished.connect(self._on_task_finished)

    def _on_log(self, line):
        # 日志回调可能来自后台线程，经信号回到主线程刷新
        self._log_line.emit(line)

    def _append_log(self, line):
        self.log_view.append(line)
        bar = self.log_view.verticalScrollBar()
        bar.setValue(bar.maximum())

    def _on_task_finished(self):
        """任务自然结束（非手动停止）时刷新状态，GUI 保持运行。"""
        self.status_label.setText("任务：未运行")
        logger.info("任务已结束，可再次开始")

    # --------------------------------------------------------------- hotkey
    def _setup_hotkeys(self):
        bindings = {
            "f5": lambda: self._hotkey.emit("stop"),
            "f7": lambda: self._hotkey.emit("print"),
        }
        self._registered_hotkeys = register_hotkeys(bindings)
        # 兜底：GUI 获得焦点时也能按 F5 / F7
        sc1 = QShortcut(QKeySequence("F5"), self)
        sc1.activated.connect(lambda: self._hotkey.emit("stop"))
        sc2 = QShortcut(QKeySequence("F7"), self)
        sc2.activated.connect(lambda: self._hotkey.emit("print"))

    def _handle_hotkey(self, action):
        if action == "stop":
            self.stop_task()
        elif action == "print":
            self.print_text_coords()

    # ------------------------------------------------------------- handlers
    def start_task(self):
        if self.runner.is_running():
            logger.warn("已有任务运行中，请先停止")
            return
        if focus_genshin():
            logger.info("已切换到原神窗口")
        else:
            logger.warn("未找到原神窗口，保持当前窗口")
        mode = self.settings["task_mode"]
        try:
            self.runner.start(mode)
        except Exception as e:
            logger.error(f"启动任务失败：{e}")
            return
        self.status_label.setText("任务：运行中")
        logger.info(f"点击开始，模式：{config.mode_label(mode)}")

    def stop_task(self):
        if not self.runner.is_running():
            logger.warn("当前没有运行中的任务")
            return
        self.runner.stop()
        self.status_label.setText("任务：已停止")
        logger.info("收到停止指令")

    def print_text_coords(self):
        logger.info("开始识别原神窗口内的文字…")
        if focus_genshin():
            logger.info("已切换到原神窗口")
        else:
            logger.warn("未找到原神窗口，保持当前窗口")

        rect = game_client_rect()
        if rect is None:
            logger.warn("无法获取原神窗口区域，改为全屏识别（坐标相对全屏）")
            region = None
        else:
            region = rect
            logger.info(f"识别区域：原神窗口 {rect}（坐标相对窗口）")

        def work():
            try:
                lines = scan_text(region=region)
            except Exception as e:
                logger.error(f"OCR 识别失败：{e}")
                return
            if not lines:
                logger.warn("未识别到任何文字")
                return
            for line in lines:
                logger.info(f"{line.text}  @ {line.box}  置信度 {line.score:.2f}")
            logger.info(f"共识别 {len(lines)} 条文字（坐标相对原神窗口）")
        threading.Thread(target=work, daemon=True).start()

    def clear_logs(self):
        self.log_view.clear()

    def save_settings(self):
        self.settings["task_mode"] = self.mode_combo.currentData()
        config.save_settings(self.settings)
        self._refresh_mode_text()
        logger.info(f"设置已保存，当前模式：{config.mode_label(self.settings['task_mode'])}")

    def _refresh_mode_text(self):
        self.start_btn.setText(f"开始千星奇域{config.mode_label(self.settings['task_mode'])}")


def is_admin():
    """是否以管理员运行。"""
    try:
        return bool(ctypes.windll.shell32.IsUserAnAdmin())
    except Exception:
        return False


def run_as_admin():
    """以管理员权限重新拉起本脚本，返回是否成功。"""
    try:
        ctypes.windll.shell32.ShellExecuteW(
            None, "runas", sys.executable, __file__, None, 1
        )
        return True
    except Exception:
        return False


def main():
    """启动入口。"""
    # 与原神交互需要管理员权限（否则点击/按键会被拦截）
    if not is_admin():
        if run_as_admin():
            sys.exit(0)
        import tkinter
        from tkinter import messagebox
        root = tkinter.Tk()
        root.withdraw()
        messagebox.showerror(
            "权限错误",
            "需要管理员权限才能与原神窗口交互。请右键以管理员身份运行本脚本。",
        )
        root.destroy()
        sys.exit(1)

    app = QApplication(sys.argv)

    # 字体：优先原神字体，回退系统字体
    fonts.apply_default_font()

    # 皮肤
    if os.path.exists(STYLE_PATH):
        with open(STYLE_PATH, encoding="utf-8") as f:
            app.setStyleSheet(f.read())

    window = MainWindow()
    window.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
