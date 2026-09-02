"""线程安全的日志模块。

任何线程调用 logger.info/warn/error 都会通过 Qt 信号回到 GUI 主线程刷新，
因此可以在后台任务线程里随意打日志。
"""
import logging


class _QtHandler(logging.Handler):
    """把日志转发给 GUI 提供的回调（通常是 Qt 信号 emit）。"""

    def __init__(self, emit):
        """emit: callable(line: str)，在日志产生的线程被调用。"""
        super().__init__(level=logging.INFO)
        self._emit = emit

    def emit(self, record):
        try:
            self._emit(self.format(record))
        except Exception:
            pass


def setup(emit):
    """安装日志处理器。重复调用会替换旧处理器。"""
    root = logging.getLogger()
    root.setLevel(logging.INFO)
    for handler in list(root.handlers):
        if isinstance(handler, _QtHandler):
            root.removeHandler(handler)
    handler = _QtHandler(emit)
    handler.setFormatter(
        logging.Formatter("[%(asctime)s][%(levelname)s] %(message)s", datefmt="%H:%M:%S")
    )
    root.addHandler(handler)
    root.propagate = False


def info(message):
    logging.info(message)


def warn(message):
    logging.warning(message)


def error(message):
    logging.error(message)
