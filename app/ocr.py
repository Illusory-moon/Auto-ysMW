"""屏幕截图 + OCR 文字识别。

依赖 rapidocr_onnxruntime，返回文字及其在屏幕上的坐标。
"""
from dataclasses import dataclass

from PIL import ImageGrab


@dataclass
class TextLine:
    """一条识别结果。box 为 (左上x, 左上y, 右下x, 右下y)。"""

    text: str
    box: tuple[int, int, int, int]
    score: float


def capture(region=None):
    """截取屏幕。region: (left, top, right, bottom)，None 表示全屏。"""
    return ImageGrab.grab(bbox=region)


def _to_bgr(image):
    import numpy as np

    arr = np.asarray(image)
    if arr.ndim == 3 and arr.shape[2] >= 3:
        return arr[:, :, ::-1]  # RGB -> BGR
    return arr


_engine = None


def _get_engine():
    global _engine
    if _engine is None:
        from rapidocr_onnxruntime import RapidOCR

        _engine = RapidOCR()
    return _engine


def scan_text(region=None) -> list[TextLine]:
    """识别屏幕指定区域（默认全屏）上的文字，返回带坐标的列表。"""
    image = capture(region)
    bgr = _to_bgr(image)
    result, _ = _get_engine()(bgr)
    lines: list[TextLine] = []
    if not result:
        return lines
    for box, text, score in result:
        xs = [point[0] for point in box]
        ys = [point[1] for point in box]
        x1, y1 = int(min(xs)), int(min(ys))
        x2, y2 = int(max(xs)), int(max(ys))
        lines.append(TextLine(text=text, box=(x1, y1, x2, y2), score=float(score)))
    return lines
