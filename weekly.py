"""千星奇域 周常流程（共 16 次）。

使用前提：从千星主界面启动（见 README）。
坐标均为原神窗口相对坐标（1920x1080 客户区）。
行走时长可用 record.py 录制，自动写入 action/movement.json 后本流程读取。
"""
import json
import os

from app import logger, ops

from app.paths import app_dir

MOVEMENT_PATH = os.path.join(app_dir(), "action", "movement.json")

# ========================= 可调参数 =========================
LOOP_TIMES = 16
SEARCH_GUID = "19940651711"

# 第一次进入：人气奇域搜索
SEARCH_BTN = (1670, 35, 1761, 62)     # 搜索奇域
SEARCH_INPUT = (1015, 131, 1396, 157)  # 关键词/GUID 输入框
LEVEL_ITEM = (248, 488, 420, 514)      # 选中关卡
START_GAME = (1542, 919, 1661, 953)    # 开始游戏

# 之后从背包-历史进入
MANAGE_LEVEL_BTN = (1513, 35, 1603, 62)   # 管理关卡
MANAGE_BTN = (1735, 1005, 1785, 1034)     # 管理
CHECKBOX = (1584, 266, 1619, 305)         # 勾选当前奇域
DELETE_SELECTED = (1715, 1007, 1804, 1033)  # 删除所选
CONFIRM = (1148, 739, 1214, 775)          # 确认（两次）
HISTORY_BTN = (1761, 1006, 1811, 1034)    # 历史
HISTORY_LEVEL = (1449, 129, 1642, 155)       # 历史中的奇域

# 奇域内 / 回大世界判定
OPEN_WORLD_TEXT = "Alt+N"
# 回到大世界的提示可能出现的位置（任一命中即可）
OPEN_WORLD_BOXES = [(257, 1027, 315, 1051), (330, 1025, 396, 1050)]
EXIT_TEXT = "退出奇域"
EXIT_BOX = (1221, 524, 1337, 555)          # 终点检测区
BACK_TO_LOBBY = (1331, 1002, 1448, 1037)   # 返回大厅
LEVELUP_CLOSE = (900, 1000)                # 等级提升弹窗关闭位置
HP_BOX = (896, 1002, 1026, 1021)           # 血条（进入判定）
HP_PATTERN = r"\d+\s*[/／]\s*\d+"          # 形如 10000/10000
LOAD_TIMEOUT = 60.0                        # 等待进入的最长时间（按血条判断）

# 行走时长（record.py 录制后自动更新，这里是默认值）
DEFAULT_LEFT = 0.8     # A 左走
DEFAULT_FORWARD = 2.0  # W 前走
DEFAULT_RIGHT = 0.0    # D 右移（可选微调，未录制则不移动）
# ============================================================


def _move(key, default):
    """从 action/movement.json 读取行走时长，缺省用默认值。"""
    try:
        with open(MOVEMENT_PATH, encoding="utf-8-sig") as f:
            data = json.load(f)
        return float(data.get(key, default))
    except Exception:
        return default


def _first_search_entry(stop_event):
    """第一次：F6 进入人气奇域，搜索 GUID 后进入。"""
    logger.info("第一次进入：人气奇域搜索")
    ops.wait(1.0, stop_event)  # 切到游戏后静默 1 秒，避免点太快
    ops.press_key("f6")
    ops.wait(1.0, stop_event)  # 等待人气奇域界面稳定再点
    ops.click_box(SEARCH_BTN)
    ops.wait(0.5, stop_event)
    ops.click_box(SEARCH_INPUT)
    ops.wait(0.3, stop_event)
    ops.type_text(SEARCH_GUID)
    ops.wait(0.3, stop_event)
    ops.press_key("enter")
    ops.wait(0.5, stop_event)
    ops.click_box(LEVEL_ITEM)
    ops.wait(0.5, stop_event)
    ops.click_box(START_GAME)


def _in_wonderland(stop_event):
    """奇域内：等待加载、走路、退出、返回大厅。"""
    logger.info("进入奇域，等待血条出现（确认加载完成）…")
    if not ops.wait_pattern(HP_PATTERN, HP_BOX, timeout=LOAD_TIMEOUT, stop_event=stop_event):
        logger.warn(f"{LOAD_TIMEOUT:.0f}s 内未识别到血条，继续（请确认已进入）")
    ops.hold_key("a", _move("a", DEFAULT_LEFT), stop_event)
    ops.hold_key("w", _move("w", DEFAULT_FORWARD), stop_event)
    ops.hold_key("d", _move("d", DEFAULT_RIGHT), stop_event)

    # 终点判定：识别到【退出奇域】则按 F；否则提示（图像识别 final.png 暂未启用）
    if ops.wait_text(EXIT_TEXT, EXIT_BOX, timeout=20, stop_event=stop_event):
        ops.press_key("f")
        logger.info("已按 F 退出奇域")
    else:
        logger.warn("未识别到【退出奇域】文字（final.png 图像识别暂未启用），继续等待返回大厅")

    # 返回大厅：识别到就点；长时间没识别到可能是等级提升弹窗（每4把升级，10的倍数弹窗），先关掉再试
    if ops.wait_text("返回大厅", BACK_TO_LOBBY, timeout=15, stop_event=stop_event):
        ops.click_box(BACK_TO_LOBBY)
    else:
        logger.warn("长时间未识别到【返回大厅】，可能是等级提升弹窗，点击 (900,1000) 关闭")
        ops.click_point(*LEVELUP_CLOSE)
        ops.wait(1.0, stop_event)
        if stop_event.is_set():
            return
        if ops.wait_text("返回大厅", BACK_TO_LOBBY, timeout=10, stop_event=stop_event):
            ops.click_box(BACK_TO_LOBBY)
        else:
            ops.wait(3, stop_event)
            ops.click_box(BACK_TO_LOBBY)


def _delete_and_select_next(stop_event):
    """返回大厅后：等待回到大世界（Alt+N），再背包-管理-删除，从历史选下一个。"""
    logger.info("管理奇域：删除当前，从历史选择下一个")
    if ops.wait_text(OPEN_WORLD_TEXT, OPEN_WORLD_BOXES, timeout=15, stop_event=stop_event):
        ops.wait(1.0, stop_event)  # 静默 1 秒等待画面稳定
    else:
        logger.warn("未识别到 Alt+N，按等待 5 秒处理")
        ops.wait(5, stop_event)
    ops.press_key("b")
    ops.wait(1.0, stop_event)
    ops.click_box(MANAGE_LEVEL_BTN)
    ops.wait(0.5, stop_event)
    ops.click_box(MANAGE_BTN)
    ops.wait(0.8, stop_event)
    ops.click_box(CHECKBOX)
    ops.wait(0.3, stop_event)
    ops.click_box(DELETE_SELECTED)
    ops.wait(0.4, stop_event)
    ops.click_box(CONFIRM)
    ops.wait(0.5, stop_event)
    ops.click_box(CONFIRM)
    ops.wait(3.5, stop_event)  # 静默 3.5 秒等删除动画
    ops.press_key("esc")
    ops.wait(0.5, stop_event)
    ops.click_box(HISTORY_BTN)
    ops.wait(0.8, stop_event)
    ops.click_box(HISTORY_LEVEL)
    ops.wait(0.5, stop_event)
    ops.click_box(START_GAME)


def run_weekly(stop_event):
    """执行周常：第一次搜索进入，之后背包-历史进入，共 16 次，完成按 F1。"""
    if stop_event.is_set():
        return

    _first_search_entry(stop_event)

    for run_index in range(1, LOOP_TIMES + 1):
        if stop_event.is_set():
            logger.info("收到停止信号，周常提前结束")
            return
        logger.info(f"=== 第 {run_index}/{LOOP_TIMES} 次奇域 ===")
        _in_wonderland(stop_event)
        if stop_event.is_set():
            return
        if run_index < LOOP_TIMES:
            _delete_and_select_next(stop_event)
        if stop_event.is_set():
            return

    logger.info("周常完成（16/16）！确认回到大世界…")
    if ops.wait_text(OPEN_WORLD_TEXT, OPEN_WORLD_BOXES, timeout=15, stop_event=stop_event):
        ops.wait(1.0, stop_event)  # 静默 1 秒等画面稳定
    else:
        logger.warn("未识别到 Alt+N，直接按 F1")
    if stop_event.is_set():
        logger.info("收到停止信号，跳过 F1")
        return
    ops.press_key("f1")
    logger.info("已按 F1：本周经验已满")
