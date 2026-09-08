"""任务线程管理：在后台线程运行状态机，支持开始 / 停止。"""
import threading

from core.state_machine import run_mode

from . import config, logger


class TaskRunner:
    def __init__(self, on_finish=None):
        self._thread = None
        self._stop_event = threading.Event()
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
        self._thread = threading.Thread(target=self._run, name="千星奇域任务", daemon=True)
        self._thread.start()

    def _run(self):
        logger.info(f"任务线程启动，模式：{config.mode_label(self._mode)}")
        try:
            run_mode(self._mode, self._stop_event)
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
        """请求正在运行的任务停止。"""
        self._stop_event.set()
