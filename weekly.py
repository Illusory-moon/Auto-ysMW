"""千星奇域 周常流程（共 16 次）。

使用前提：从千星主界面启动（见 README）。
坐标均为原神窗口相对坐标（1920x1080 客户区）。
行走时长可用 record.py 录制，自动写入 action/movement.json 后本流程读取。
"""
import json
import os
from dataclasses import dataclass

from app import logger, ops
from app.paths import app_dir

MOVEMENT_PATH = os.path.join(app_dir(), "action", "movement.json")

# ========================= 可调参数 =========================
LOOP_TIMES = 16

# 服务器判定：按右下角 UID 区分官服 / B服
UID_BOX = (1683, 1051, 1863, 1077)   # 右下角 UID 区域
UID_THRESHOLD = 500_000_000          # UID 大于此值为 B服，否则官服

# 第一次进入：人气奇域搜索
SEARCH_BTN = (1670, 35, 1761, 62)     # 搜索奇域
SEARCH_INPUT = (1015, 131, 1396, 157)  # 关键词/GUID 输入框
LEVEL_ITEM = (248, 488, 420, 514)      # 选中关卡
START_GAME = (1542, 919, 1661, 953)    # 开始游戏（位置不变，文字随状态变化）

# 第一次进入时封面按钮状态：从大世界进入会先显示「前往大厅」，加载完再显示进入按钮
GO_TO_LOBBY_TEXT = "前往大厅"
# B服是多人地图，进入按钮是「单人挑战」（位置与官服开始按钮不同）
SOLO_TEXT = "单人挑战"
SOLO_BOX = (1229, 916, 1352, 960)   # B服「单人挑战」按钮位置

# 之后从背包-历史进入
MANAGE_LEVEL_BTN = (1513, 35, 1603, 62)   # 管理关卡
MANAGE_BTN = (1735, 1005, 1785, 1034)     # 管理
CHECKBOX = (1584, 266, 1619, 305)         # 勾选当前奇域
# 管理删除列表：要删除的关卡不一定在列表最上方，需按名字定位（x1,y1,x2,y2）
DELETE_LIST = (210, 246, 599, 955)      # 管理列表关卡名区域
DELETE_ROW_OFFSET = 20                  # 点击选中框：文字中心往下 20px（不点文字本身）
DELETE_SELECTED = (1715, 1007, 1804, 1033)  # 删除所选
CONFIRM = (1148, 739, 1214, 775)          # 确认（两次）
HISTORY_BTN = (1761, 1006, 1811, 1034)    # 历史

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

@dataclass(frozen=True)
class ServerConfig:
    name: str
    search_guid: str
    history_list: tuple[int, int, int, int]
    history_text: tuple[str, ...]
    walk: tuple[tuple[str, float], ...]
    use_movement: bool
    enter_texts: tuple[str, ...]
    enter_box: tuple[int, int, int, int]
    need_exit: bool


# ===== 服务器配置（按 UID 自动选用）=====
# 官服：目标奇域「抑郁快速筛查工具」；局内按 A/W/D 走（时长读 movement.json）
OFFICIAL = ServerConfig(
    name="官服",
    search_guid="19940651711",
    history_list=(1445, 107, 1645, 1033),
    history_text=("抑郁快速筛查工具", "筛查工具"),
    walk=(("a", DEFAULT_LEFT), ("w", DEFAULT_FORWARD), ("d", DEFAULT_RIGHT)),
    use_movement=True,
    enter_texts=("开始奇域", "开始游戏"),
    enter_box=START_GAME,
    need_exit=True,
)
# B服：奇域编号 20333726902，名字「成就结算吃金币通关01」字多需往右扩；局内 W 4 秒即结算
BILI = ServerConfig(
    name="B服",
    search_guid="20333726902",
    history_list=(1445, 107, 1700, 1033),
    history_text=("成就结算吃金币通关01",),
    walk=(("w", 4.0),),
    use_movement=False,
    enter_texts=(SOLO_TEXT,),
    enter_box=SOLO_BOX,
    need_exit=False,
)
# ============================================================


def _move(key, default):
    """从 action/movement.json 读取行走时长，缺省用默认值。"""
    try:
        with open(MOVEMENT_PATH, encoding="utf-8-sig") as f:
            data = json.load(f)
        return float(data.get(key, default))
    except Exception:
        return default


def _resolve_walk(server):
    """返回当前服务器的局内行走计划 [(按键, 时长)]。

    官服按 A/W/D 走（时长读 movement.json）；B服只 W 前走固定时长即可结算。
    """
    if server.use_movement:
        return [(key, _move(key, default)) for key, default in server.walk]
    return list(server.walk)


def _detect_server(stop_event):
    """按右下角 UID 判断服务器，返回对应的服务器配置字典。"""
    uid = ops.read_uid(UID_BOX, timeout=8, stop_event=stop_event)
    if uid is None:
        logger.warn("未识别到 UID，默认使用官服配置")
        return OFFICIAL
    is_bili = uid > UID_THRESHOLD
    logger.info(f"检测到 UID={uid}，判定为{'B服' if is_bili else '官服'}")
    return BILI if is_bili else OFFICIAL


def _first_search_entry(stop_event, server):
    """第一次：F6 进入人气奇域，搜索 GUID 后进入。

    从大世界进入时，点击封面后按钮会先显示【前往大厅】，点击后经历加载动画，
    再显示进入按钮【官服：开始奇域/开始游戏；B服：单人挑战】（B服位置不同）；
    若已在大厅则直接显示进入按钮。返回是否成功进入下一阶段。
    """
    logger.info("第一次进入：人气奇域搜索")
    ops.wait(1.0, stop_event)  # 切到游戏后静默 1 秒，避免点太快
    if stop_event.is_set():
        return False
    ops.press_key("f6")
    ops.wait(1.0, stop_event)  # 等待人气奇域界面稳定再点
    if stop_event.is_set():
        return False
    ops.click_box(SEARCH_BTN)
    ops.wait(0.5, stop_event)
    if stop_event.is_set():
        return False
    ops.click_box(SEARCH_INPUT)
    ops.wait(0.3, stop_event)
    if stop_event.is_set():
        return False
    ops.press_key("ctrl+a")
    ops.type_text(server.search_guid)
    ops.wait(0.3, stop_event)
    if stop_event.is_set():
        return False
    ops.press_key("enter")
    ops.wait(0.5, stop_event)
    if stop_event.is_set():
        return False
    ops.click_box(LEVEL_ITEM)
    ops.wait(0.8, stop_event)

    # 区分当前状态：从大世界进入显示【前往大厅】；否则直接显示进入按钮
    # 官服进入按钮【开始奇域/开始游戏】在 START_GAME；B服进入按钮【单人挑战】在 SOLO_BOX
    ent_texts = server.enter_texts
    enter_box = server.enter_box
    detect_boxes = [START_GAME, enter_box] if enter_box != START_GAME else [START_GAME]

    hit = ops.wait_any_text(
        (GO_TO_LOBBY_TEXT, *ent_texts), detect_boxes, timeout=10, stop_event=stop_event
    )
    if stop_event.is_set():
        return False
    if hit == GO_TO_LOBBY_TEXT:
        logger.info("识别到【前往大厅】：从大世界进入，点击后等待加载动画…")
        ops.click_box(START_GAME)
        if stop_event.is_set():
            return False
        if not ops.wait_text(ent_texts, enter_box, timeout=20, stop_event=stop_event):
            if stop_event.is_set():
                return False
            logger.error(f"阶段失败：点击【前往大厅】后未识别到【{ent_texts[0]}】")
            return False
        logger.info(f"加载完成，识别到【{ent_texts[0]}】，点击进入")
        ops.wait(0.3, stop_event)  # 加载动画后按钮稳定一点再点
        if stop_event.is_set():
            return False
        ops.click_box(enter_box)
    elif hit is not None:
        logger.info(f"识别到【{hit}】，直接进入")
        ops.click_box(enter_box)
    else:
        if stop_event.is_set():
            return False
        logger.error(f"阶段失败：点击封面后未识别到【前往大厅】或【{ent_texts[0]}】")
        return False
    return True


def _in_wonderland(stop_event, server):
    """奇域内：等待加载、走路、退出、返回大厅。

    返回值表示是否完成了一个完整的“奇域 -> 大厅”状态迁移。
    关键识别失败时停止推进，避免在未知界面继续发送按键/点击。
    """
    logger.info("进入奇域，等待血条出现（确认加载完成）…")
    if not ops.wait_pattern(
        HP_PATTERN, HP_BOX, timeout=LOAD_TIMEOUT, stop_event=stop_event,
        full_window_fallback=True,
    ):
        if stop_event.is_set():
            return False
        logger.error(f"阶段失败：{LOAD_TIMEOUT:.0f}s 内未识别到血条，停止本轮")
        return False
    for key, dur in _resolve_walk(server):
        ops.hold_key(key, dur, stop_event)
    if stop_event.is_set():
        return False

    # 终点判定：官服需识别【退出奇域】并按 F；B服吃满金币无提示自动结算，直接等【返回大厅】
    if server.need_exit:
        if ops.wait_text(EXIT_TEXT, EXIT_BOX, timeout=20, stop_event=stop_event):
            ops.press_key("f")
            logger.info("已按 F 退出奇域")
        else:
            if stop_event.is_set():
                return False
            logger.error("阶段失败：未识别到【退出奇域】文字，停止本轮")
            return False

    return _return_to_lobby(stop_event)


def _return_to_lobby(stop_event):
    """结算后返回大厅，处理可能遮挡按钮的升级弹窗。"""
    if stop_event.is_set():
        return False
    if ops.wait_text("返回大厅", BACK_TO_LOBBY, timeout=15, stop_event=stop_event):
        ops.click_box(BACK_TO_LOBBY)
        logger.info("阶段完成：已返回大厅")
        return True
    else:
        logger.warn("长时间未识别到【返回大厅】，可能是等级提升弹窗，点击 (900,1000) 关闭")
        if stop_event.is_set():
            return False
        ops.click_point(*LEVELUP_CLOSE)
        ops.wait(1.0, stop_event)
        if stop_event.is_set():
            return False
        if ops.wait_text("返回大厅", BACK_TO_LOBBY, timeout=10, stop_event=stop_event):
            ops.click_box(BACK_TO_LOBBY)
            logger.info("阶段完成：关闭等级弹窗后返回大厅")
            return True
        else:
            logger.error("阶段失败：关闭等级弹窗后仍未识别到【返回大厅】")
            return False


def _delete_and_select_next(stop_event, server):
    """返回大厅后：等待回到大世界（Alt+N），再背包-管理-删除，从历史选下一个。"""
    logger.info("管理奇域：删除当前，从历史选择下一个")
    if ops.wait_text(OPEN_WORLD_TEXT, OPEN_WORLD_BOXES, timeout=15, stop_event=stop_event):
        ops.wait(1.0, stop_event)  # 静默 1 秒等待画面稳定
    else:
        if stop_event.is_set():
            return False
        # 兜底：未识别到 Alt+N 不中止（B服等可能不出现该提示），静默 5 秒后按 B 继续
        logger.warn("15s 内未识别到 Alt+N，按兜底继续（假定已回到开放世界，即将按 B）")
        ops.wait(5, stop_event)
    if stop_event.is_set():
        return False
    ops.press_key("b")
    ops.wait(1.0, stop_event)
    ops.click_box(MANAGE_LEVEL_BTN)
    ops.wait(0.5, stop_event)
    ops.click_box(MANAGE_BTN)
    ops.wait(0.8, stop_event)
    # 当前要删除的关卡不一定在列表最上方，需按名字定位后点击其选中框
    # x 用现有选定关卡位置（CHECKBOX 中心），y 用文字中心往下 20px，不点文字本身
    del_box = ops.locate_text(server.history_text, DELETE_LIST, timeout=10, stop_event=stop_event)
    if del_box is None:
        if stop_event.is_set():
            return False
        logger.error(f"阶段失败：管理列表未找到目标关卡【{server.history_text[0]}】")
        return False
    del_cy = int((del_box[1] + del_box[3]) / 2)
    del_x = (CHECKBOX[0] + CHECKBOX[2]) // 2
    logger.info(f"定位到关卡【{server.history_text[0]}】，点击其选中框 ({del_x}, {del_cy + DELETE_ROW_OFFSET})")
    ops.click_point(del_x, del_cy + DELETE_ROW_OFFSET)
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
    # 历史列表中目标奇域不一定在最上方，按名字定位后点击
    target = ops.locate_text(server.history_text, server.history_list, timeout=10, stop_event=stop_event)
    if target is None:
        if stop_event.is_set():
            return False
        logger.error(f"阶段失败：历史列表未找到目标奇域【{server.history_text[0]}】")
        return False
    logger.info(f"已定位历史奇域，点击选中 {target}")
    ops.click_box(target)
    ops.wait(0.5, stop_event)
    # 进入按钮：官服【开始游戏】在 START_GAME；B服【单人挑战】在 SOLO_BOX
    ops.click_box(server.enter_box)
    if stop_event.is_set():
        return False
    logger.info("阶段完成：已选择历史奇域并开始下一次")
    return True


def run_weekly(stop_event):
    """执行周常：第一次搜索进入，之后背包-历史进入，共 16 次，完成按 F1。"""
    if stop_event.is_set():
        return

    server = _detect_server(stop_event)
    logger.info(f"使用服务器配置：{server.name}")

    if not _first_search_entry(stop_event, server):
        logger.error("周常终止：第一次进入未成功")
        return

    for run_index in range(1, LOOP_TIMES + 1):
        if stop_event.is_set():
            logger.info("收到停止信号，周常提前结束")
            return
        logger.info(f"=== 第 {run_index}/{LOOP_TIMES} 次奇域 ===")
        if not _in_wonderland(stop_event, server):
            logger.error(f"周常中止：第 {run_index} 次未完成‘奇域 -> 大厅’")
            return
        if stop_event.is_set():
            return
        if run_index < LOOP_TIMES:
            if not _delete_and_select_next(stop_event, server):
                logger.error(f"周常中止：第 {run_index} 次未完成‘大厅 -> 下一次开始’")
                return
        if stop_event.is_set():
            return

    logger.info("周常完成（16/16）！确认回到大世界…")
    if ops.wait_text(OPEN_WORLD_TEXT, OPEN_WORLD_BOXES, timeout=15, stop_event=stop_event):
        ops.wait(1.0, stop_event)  # 静默 1 秒等画面稳定
    else:
        logger.error("周常结束失败：未识别到 Alt+N，不按 F1")
        return
    if stop_event.is_set():
        logger.info("收到停止信号，跳过 F1")
        return
    ops.press_key("f1")
    logger.info("已按 F1：本周经验已满")
