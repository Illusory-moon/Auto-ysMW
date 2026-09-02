"""千星奇域 状态机。

- 周常模式：执行 core/weekly.py 的 16 次循环流程（点击运行后工作）。
- 日常模式：暂未实现，占位等待。
"""
import time

from app import logger
from app.config import mode_label


class StateMachine:
    def __init__(self, stop_event, mode):
        self._stop = stop_event
        self.mode = mode
        self.state = "start"

    # ---- 供状态机内部使用 ----
    def is_stop(self):
        return self._stop.is_set()

    def next(self, state):
        self.state = state

    # ---- 生命周期 ----
    def on_stop(self):
        """收到停止请求时调用，可用于清理资源。这里先空实现。"""
        pass

    def run(self):
        logger.info(f"状态机开始（模式：{mode_label(self.mode)}）")
        try:
            if self.mode == "weekly":
                from weekly import run_weekly
                run_weekly(self._stop)
            else:
                logger.info("[占位] 日常模式暂未实现")
                self._wait_until_stop()
        finally:
            logger.info("状态机结束")

    def _wait_until_stop(self):
        """没有任务时占位等待，直到收到停止信号。"""
        while not self.is_stop():
            time.sleep(1)
