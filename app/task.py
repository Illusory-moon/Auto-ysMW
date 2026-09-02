"""任务线程管理：在后台线程运行状态机，支持开始 / 停止。"""
import threading

from . import config, logger
from core.state_machine import StateMachine


class TaskRunner:
    def __init__(self, on_finish=None):
        self._thread = None
        self._stop_event = threading.Event()
        self._machine = None
        self._mode = config.DEFAULT_MODE
        self._on_finish = on_finish  # 任务线程结束时回调（在后台线程调用）

    def is_running(self):
        return self._thread is not None and self._thread.is_alive()

    def start(self, mode):
        """启动任务。mode: 'daily' / 'weekly'。"""
        if self.is_running():
            raise RuntimeError("已有任务运行中")
        self._mode = mode
        self._stop_event.clear()
        self._machine = StateMachine(self._stop_event, mode)
        self._thread = threading.Thread(target=self._run, name="千星奇域任务", daemon=True)
        self._thread.start()

    def _run(self):
        logger.info(f"任务线程启动，模式：{config.mode_label(self._mode)}")
        try:
            self._machine.run()
        except Exception as e:
            logger.error(f"任务异常结束：{e}")
        finally:
            logger.info("任务线程已退出")
            if self._on_finish is not None:
                try:
                    self._on_finish()
                except Exception:
                    pass

    def stop(self):
        """请求停止：置停止位并通知状态机清理。"""
        if self._machine is not None:
            self._stop_event.set()
            self._machine.on_stop()
