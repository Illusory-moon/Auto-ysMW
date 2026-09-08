"""按配置的模式运行任务。"""

from app import logger
from app.config import mode_label


def run_mode(mode, stop_event):
    """运行指定模式；每个模式只需提供一个接收停止事件的入口。"""
    logger.info(f"任务开始（模式：{mode_label(mode)}）")
    try:
        if mode == "weekly":
            from weekly import run_weekly

            run_weekly(stop_event)
        elif mode == "daily":
            from daily import run_daily

            run_daily(stop_event)
        else:
            raise ValueError(f"未知任务模式：{mode}")
    finally:
        logger.info("任务结束")
