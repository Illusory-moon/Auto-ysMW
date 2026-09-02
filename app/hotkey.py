"""全局热键封装。

当前基于 keyboard 库实现全局热键（游戏窗口聚焦时也能生效）。
若注册失败（例如权限不足），会静默忽略，GUI 内仍可用 QShortcut 兜底。
"""
import keyboard

_registered = []


def register(bindings):
    """注册全局热键。bindings: {键名: 回调}。返回成功注册的键名列表。"""
    ok = []
    for key, callback in bindings.items():
        try:
            keyboard.add_hotkey(key, callback, suppress=False)
            ok.append(key)
        except Exception:
            pass
    _registered.extend(ok)
    return ok


def unregister_all():
    for key in _registered:
        try:
            keyboard.remove_hotkey(key)
        except Exception:
            pass
    _registered.clear()
