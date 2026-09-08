"""日常：挑战关卡挂机一分钟后中断，再通关一次周常关卡。"""

from dataclasses import replace

import weekly
from app import logger, ops

FIRST_GUIDS = {"官服": "45694132064", "B服": "7448990007"}
START_CHALLENGE = (1645, 1003, 1763, 1036)
INTERRUPT_CHALLENGE = (919, 583, 1036, 616)
CHARACTER_POINTS = ((463, 530), (101, 178), (429, 1016))
IDLE_SECONDS = 60.0


def _click_text(text, box, stop_event, timeout=20):
    if not ops.wait_text(text, box, timeout=timeout, stop_event=stop_event):
        if not stop_event.is_set():
            logger.error(f"日常中止：未识别到【{text}】")
        return False
    if stop_event.is_set():
        return False
    ops.click_box(box)
    return True


def _wait_for_game(stop_event):
    return ops.wait_pattern(
        weekly.HP_PATTERN, weekly.HP_BOX,
        timeout=weekly.LOAD_TIMEOUT, stop_event=stop_event,
        full_window_fallback=True,
    ) and not stop_event.is_set()


def _first_challenge(stop_event):
    if not _click_text("开始挑战", START_CHALLENGE, stop_event):
        return False
    if not _wait_for_game(stop_event):
        if stop_event.is_set():
            return False
        # 超时不能证明缺角色；只在仍停留于编队界面时尝试一次补选。
        if not ops.wait_text("开始挑战", START_CHALLENGE, timeout=3, stop_event=stop_event):
            logger.error("日常中止：未识别到血条，且无法确认编队界面")
            return False
        logger.warn("未识别到血条且仍显示开始挑战，尝试补选第一个角色（仅一次）")
        for point in CHARACTER_POINTS:
            if stop_event.is_set():
                return False
            ops.click_point(*point)
            ops.wait(1.0, stop_event)
        if not _click_text("开始挑战", START_CHALLENGE, stop_event):
            return False
        if not _wait_for_game(stop_event):
            if not stop_event.is_set():
                logger.error("日常中止：补选角色后仍未识别到血条")
            return False

    logger.info("关卡1已进入，挂机60秒")
    ops.wait(IDLE_SECONDS, stop_event)
    if stop_event.is_set():
        return False
    ops.press_key("esc")
    if not _click_text("中断挑战", INTERRUPT_CHALLENGE, stop_event):
        return False
    return weekly._return_to_lobby(stop_event)


def _wait_for_lobby(stop_event):
    """结算关闭后等待大厅/开放世界 HUD，避免在加载中打开搜索。"""
    ready = ops.wait_pattern(
        rf"{weekly.HP_PATTERN}|Alt\s*\+\s*N",
        [weekly.HP_BOX, *weekly.OPEN_WORLD_BOXES],
        timeout=weekly.LOAD_TIMEOUT, stop_event=stop_event,
        full_window_fallback=True,
    )
    if not ready or stop_event.is_set():
        if not stop_event.is_set():
            logger.error("日常中止：返回后未识别到大厅血条或 Alt+N")
        return False
    ops.wait(1.0, stop_event)
    return not stop_event.is_set()


def run_daily(stop_event):
    """依次搜索并通关两关；任何阶段失败或停止都不进入下一阶段。"""
    if stop_event.is_set():
        return
    server = weekly._detect_server(stop_event)
    if stop_event.is_set():
        return
    first = replace(
        server, search_guid=FIRST_GUIDS[server.name],
        enter_texts=weekly.OFFICIAL.enter_texts, enter_box=weekly.START_GAME,
    )
    logger.info(f"日常关卡1（{server.name}）：{first.search_guid}")
    if not weekly._first_search_entry(stop_event, first):
        return
    if not _first_challenge(stop_event) or not _wait_for_lobby(stop_event):
        return
    logger.info(f"日常关卡2（{server.name}）：{server.search_guid}")
    if not weekly._first_search_entry(stop_event, server):
        return
    if not weekly._in_wonderland(stop_event, server) or not _wait_for_lobby(stop_event):
        return
    logger.info("日常完成：两关均已通关并返回大厅")
