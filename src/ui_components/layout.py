# ui_components/layout.py
import cv2
import numpy as np


def compose_side(
    ui,                 # DroneUI インスタンス
    frame,
    display_w: int,
    display_h: int,
    *,
    ui_w: int = 260,
    ui_bg=(0, 0, 0),
    interpolation=cv2.INTER_LINEAR,
    **telemetry,
):
    """
    ウィンドウ全体(display_w x display_h)に対して、
    左：映像、右：UI固定幅(ui_w) で合体した画像を返す。
    """
    if display_w <= 0 or display_h <= 0:
        raise ValueError("display_w/display_h must be positive")

    # 右パネルが大きすぎたら保険
    ui_w = int(ui_w)
    ui_w = max(1, min(ui_w, display_w - 1))

    left_w = display_w - ui_w

    if frame is None:
        frame = np.zeros((display_h, left_w, 3), dtype=np.uint8)
    else:
        # 左映像をウィンドウの左領域にぴったり合わせる
        if frame.shape[0] != display_h or frame.shape[1] != left_w:
            frame = cv2.resize(frame, (left_w, display_h), interpolation=interpolation)

    # UIは右に固定幅で合体（ui.draw が hstack してくれる）
    out = ui.draw(
        frame,
        layout="side",
        ui_width=ui_w,
        ui_bg=ui_bg,
        **telemetry,
    )
    return out
