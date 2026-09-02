"""窗口工具：将原神游戏窗口切换到前台。"""
import ctypes

try:
    import win32con
    import win32gui
except ImportError:  # 非 Windows 或不含 pywin32 时降级
    win32con = None
    win32gui = None

# 可能出现的游戏窗口标题关键字
GAME_TITLES = ("原神", "Genshin Impact")

_VK_MENU = 0x12  # Alt 键，用于绕过 Windows 的前台窗口锁定


def _find_game_window():
    """找到标题含 '原神' 的窗口句柄，找不到返回 None。"""
    if win32gui is None:
        return None

    found = [None]

    def _callback(hwnd, _):
        if found[0] is not None:
            return
        title = win32gui.GetWindowText(hwnd)
        if not title:
            return
        if any(t in title for t in GAME_TITLES):
            found[0] = hwnd

    win32gui.EnumWindows(_callback, None)
    return found[0]


def _force_foreground(hwnd):
    """尝试将窗口置顶。模拟按下 Alt 来获得置顶权限。"""
    try:
        if win32gui.IsIconic(hwnd):
            win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)
        ctypes.windll.user32.keybd_event(_VK_MENU, 0, 0, 0)  # Alt down
        win32gui.SetForegroundWindow(hwnd)
        ctypes.windll.user32.keybd_event(_VK_MENU, 0, 2, 0)  # Alt up
        return True
    except Exception:
        return False


def focus_genshin() -> bool:
    """切换到原神窗口。成功返回 True，找不到/失败返回 False。"""
    hwnd = _find_game_window()
    if hwnd is None:
        return False
    return _force_foreground(hwnd)


def game_client_rect():
    """返回原神窗口客户区在屏幕上的矩形 (left, top, right, bottom)。

    找不到窗口或获取失败返回 None。OCR 用它裁剪窗口内的画面，
    得到的结果坐标是相对该窗口的，而不是全屏。
    """
    hwnd = _find_game_window()
    if hwnd is None or win32gui is None:
        return None
    try:
        left, top = win32gui.ClientToScreen(hwnd, (0, 0))
        client = win32gui.GetClientRect(hwnd)  # (0, 0, width, height)
        right, bottom = win32gui.ClientToScreen(hwnd, (client[2], client[3]))
        return (int(left), int(top), int(right), int(bottom))
    except Exception:
        return None
