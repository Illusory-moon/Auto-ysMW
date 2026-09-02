"""低层游戏操作：点击、按键、输入、行走、OCR 等待。

所有 box 坐标均为【原神窗口相对坐标】（游戏客户区 1920x1080），
函数内部会换算成屏幕坐标后再执行。
box 参数支持单个四元组 (x1,y1,x2,y2) 或多个四元组组成的列表（任一命中即可）。
"""
import time

import keyboard

from . import logger
from .focus import focus_genshin, game_client_rect
from .ocr import scan_text


def _game_rect():
    rect = game_client_rect()
    if rect is None:
        raise RuntimeError("未找到原神窗口")
    return rect


def click_box(box):
    """点击窗口相对 box 的中心。box: [x1, y1, x2, y2]。"""
    import pyautogui

    focus_genshin()
    left, top, _, _ = _game_rect()
    x1, y1, x2, y2 = box
    cx = int(left + (x1 + x2) / 2)
    cy = int(top + (y1 + y2) / 2)
    logger.info(f"点击 ({cx}, {cy})")
    pyautogui.click(cx, cy)


def click_point(x, y):
    """点击窗口相对坐标点 (x, y)。"""
    import pyautogui

    focus_genshin()
    left, top, _, _ = _game_rect()
    cx, cy = int(left + x), int(top + y)
    logger.info(f"点击 ({cx}, {cy})")
    pyautogui.click(cx, cy)


def press_key(key):
    focus_genshin()
    keyboard.press_and_release(key)
    logger.info(f"按键 {key}")


def hold_key(key, seconds, stop_event=None):
    focus_genshin()
    keyboard.press(key)
    wait(seconds, stop_event)
    keyboard.release(key)
    logger.info(f"按住 {key} {seconds:.2f}s")


def type_text(text):
    focus_genshin()
    keyboard.write(text, delay=0.05)
    logger.info(f"输入 {text}")


def wait(seconds, stop_event=None, chunk=0.2):
    """等待 N 秒，期间响应停止信号（不阻塞停止）。"""
    deadline = time.time() + seconds
    while time.time() < deadline:
        if stop_event is not None and stop_event.is_set():
            return
        time.sleep(chunk)


def _box_regions(box, rect, margin=40):
    """把窗口相对 box（单个或列表）扩边后转成屏幕区域列表。

    box 为 None 时返回整个窗口的一个区域。
    """
    left, top, right, bottom = rect
    if box is None:
        return [(left, top, right, bottom)]
    if isinstance(box, (list, tuple)) and len(box) == 4 and all(
        isinstance(v, (int, float)) for v in box
    ):
        boxes = [box]
    else:
        boxes = list(box)
    regions = []
    for b in boxes:
        x1, y1, x2, y2 = b
        regions.append(
            (
                max(left, left + x1 - margin),
                max(top, top + y1 - margin),
                min(right, left + x2 + margin),
                min(bottom, top + y2 + margin),
            )
        )
    return regions


def wait_pattern(pattern, box=None, timeout=30.0, stop_event=None, interval=0.5, margin=40):
    """轮询 OCR，直到 box 区域内出现匹配正则 pattern 的文字。

    用于识别「血条 10000/10000」这类数值会变的 UI。
    box 为窗口相对坐标（单个或列表）；缺省扫描整个窗口。返回是否出现。
    """
    import re

    regex = re.compile(pattern)
    regions = _box_regions(box, _game_rect(), margin)

    start = time.time()
    while True:
        if stop_event is not None and stop_event.is_set():
            return False
        for region in regions:
            lines = scan_text(region=region)
            for line in lines:
                if regex.search(line.text):
                    logger.info(f"识别到：{line.text}（匹配 {pattern}）")
                    return True
        if time.time() - start >= timeout:
            return False
        time.sleep(interval)


def wait_text(text, box=None, timeout=15.0, stop_event=None, interval=0.5, margin=40):
    """轮询 OCR，直到 box 区域内出现 text。

    box 为窗口相对坐标（单个或列表，任一命中即可）；缺省扫描整个窗口。
    margin 会在 box 四边外扩一圈，避免窄框裁掉文字导致识别失败。
    返回是否出现。
    """
    regions = _box_regions(box, _game_rect(), margin)

    start = time.time()
    while True:
        if stop_event is not None and stop_event.is_set():
            return False
        for region in regions:
            lines = scan_text(region=region)
            if any(text in line.text for line in lines):
                logger.info(f"识别到：{text}")
                return True
        if time.time() - start >= timeout:
            return False
        time.sleep(interval)
