"""操作录制：在原神里走动，按 F9 结束，输出各键按住时长。

用法：
    uv run record.py

操作：切到原神，实际走一遍（A 左走 / W 前走 等），完成后按 F9。
输出：按住时长 JSON，并保存到 action/movement.json（周常流程会自动读取）。
"""
import ctypes
import json
import os
import sys

import keyboard

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
OUT_PATH = os.path.join(BASE_DIR, "action", "movement.json")
STOP_KEY = "f9"


def _is_admin():
    try:
        return bool(ctypes.windll.shell32.IsUserAnAdmin())
    except Exception:
        return False


def _run_as_admin():
    try:
        ctypes.windll.shell32.ShellExecuteW(None, "runas", sys.executable, __file__, None, 1)
        return True
    except Exception:
        return False


def main():
    if not _is_admin():
        if _run_as_admin():
            sys.exit(0)
        print("录制需要管理员权限，请以管理员身份运行。")
        sys.exit(1)

    print(f"=== 开始录制：请切到原神实际操作，按 {STOP_KEY.upper()} 结束 ===")
    events = keyboard.record(until=STOP_KEY)

    holds = {}
    down_time = {}
    taps = []
    for ev in events:
        if ev.event_type == "down" and ev.name not in down_time:
            down_time[ev.name] = ev.time
        elif ev.event_type == "up" and ev.name in down_time:
            duration = ev.time - down_time.pop(ev.name)
            if duration >= 0.15:
                holds[ev.name] = round(duration, 3)
            else:
                taps.append(ev.name)

    print("按住时长:", json.dumps(holds, ensure_ascii=False, indent=2))
    print("单击(忽略):", taps)

    os.makedirs(os.path.dirname(OUT_PATH), exist_ok=True)
    with open(OUT_PATH, "w", encoding="utf-8") as f:
        json.dump(holds, f, ensure_ascii=False, indent=2)
    print(f"已保存: {OUT_PATH}")


if __name__ == "__main__":
    main()
