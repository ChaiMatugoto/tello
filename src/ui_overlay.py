# ui_overlay.py
import cv2
import numpy as np

TEXT = (240, 240, 240)
DIM  = (170, 170, 170)
PANEL = (0, 0, 0)
CIRCLE = (200, 200, 200)
FILL = (0, 0, 0)


class DroneUI:
    """
    全画面映像の上にUIを重ねる
    - 右上：丸3つ(ROLL/PITCH/YAW)
    - その下：丸3つ(ACC X/Y/Z)
    - その下：縦バー3本(ALT / SPD / BAT)
    - 左上：SN
    - 上部：TEMP / TIME
    - 左下：コマンド
    - 右下：WiFi
    """

    def __init__(self, panel_width: int = 260, bottom_margin: int = 60):
        # 互換のため残す（今は使わない）
        self.panel_width = panel_width
        self.bottom_margin = bottom_margin

    def _blend_rect(self, img, x1, y1, x2, y2, alpha=0.45):
        x1 = max(0, min(img.shape[1] - 1, int(x1)))
        x2 = max(0, min(img.shape[1], int(x2)))
        y1 = max(0, min(img.shape[0] - 1, int(y1)))
        y2 = max(0, min(img.shape[0], int(y2)))
        if x2 <= x1 or y2 <= y1:
            return
        roi = img[y1:y2, x1:x2]
        overlay = roi.copy()
        overlay[:] = PANEL
        cv2.addWeighted(overlay, alpha, roi, 1 - alpha, 0, roi)

    def _put(self, img, text, org, scale, color=TEXT, thick=1):
        cv2.putText(img, str(text), org, cv2.FONT_HERSHEY_SIMPLEX, scale, color, thick, cv2.LINE_AA)

    def _put_right(self, img, text, right_x, y, scale, color=TEXT, thick=1):
        (tw, th), _ = cv2.getTextSize(str(text), cv2.FONT_HERSHEY_SIMPLEX, scale, thick)
        self._put(img, text, (int(right_x - tw), int(y)), scale, color, thick)

    def _circle_label(self, img, center, r, label, value=None, scale=0.55):
        cv2.circle(img, center, r, CIRCLE, -1, cv2.LINE_AA)
        cv2.circle(img, center, r, (150, 150, 150), 1, cv2.LINE_AA)

        # ラベル（中央）
        (tw, th), _ = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, scale, 1)
        self._put(img, label, (center[0] - tw // 2, center[1] + th // 2), scale, (70, 70, 70), 1)

        # 値（小さく下側） ※要らなければ消してOK
        if value is not None:
            s2 = max(0.45, scale - 0.10)
            txt = str(value)
            (tw2, th2), _ = cv2.getTextSize(txt, cv2.FONT_HERSHEY_SIMPLEX, s2, 1)
            self._put(img, txt, (center[0] - tw2 // 2, center[1] + r - 6), s2, (60, 60, 60), 1)

    def _bar(self, img, x, y, w, h, ratio):
        # 背景
        cv2.rectangle(img, (x, y), (x + w, y + h), (230, 230, 230), -1)
        cv2.rectangle(img, (x, y), (x + w, y + h), (160, 160, 160), 1)

        ratio = 0.0 if ratio is None else float(ratio)
        ratio = max(0.0, min(1.0, ratio))

        fh = int(h * ratio)
        if fh > 0:
            cv2.rectangle(img, (x, y + (h - fh)), (x + w, y + h), FILL, -1)

    def draw(
        self,
        frame,
        *,
        # 既存互換
        battery=None,
        roll=None,
        pitch=None,
        yaw=None,
        height=None,
        total_alt=None,

        # 追加で渡せたら表示（渡さなくてもOK）
        sn=None,
        temp=None,          # 温度（℃）
        flight_time=None,   # time（秒）
        agx=None, agy=None, agz=None,   # 加速度
        speed=None,         # 速度（任意単位）
        wifi=None,          # wifi強度（SNR or dBm）
        commands=None,      # 左下に出す文字列
    ):
        h, w, _ = frame.shape
        canvas = frame.copy()

        # スケールは画面幅に応じて調整
        s = max(0.6, min(1.2, w / 900.0))

        # ===== 左上：SN =====
        sn_text = f"SN: {sn if sn is not None else '--'}"
        self._blend_rect(canvas, 0, 0, int(240 * s), int(44 * s), alpha=0.35)
        self._put(canvas, sn_text, (int(14 * s), int(30 * s)), 0.9 * s, TEXT, 2)

        # ===== 上：TEMP / TIME =====
        temp_text = "--" if temp is None else str(int(temp))
        time_text = "--" if flight_time is None else str(int(flight_time))
        top_line = f"TEMP:{temp_text}  time:{time_text}s"
        self._blend_rect(canvas, int(w * 0.45), 0, w, int(44 * s), alpha=0.35)
        self._put_right(canvas, top_line, int(w - 14 * s), int(30 * s), 0.75 * s, TEXT, 2)

        # ===== 右側UIブロックの座標設計 =====
        margin = int(18 * s)
        r = int(26 * s)  # 円の半径
        r = max(20, min(r, 36))
        gap = int(14 * s)

        block_w = (2 * r) * 3 + gap * 2
        block_x0 = w - margin - block_w
        row1_y = int(80 * s)
        row2_y = row1_y + (2 * r) + int(18 * s)

        # 背景（右上の丸＋バー一帯）
        bg_x1 = block_x0 - int(12 * s)
        bg_y1 = row1_y - int(28 * s)
        bg_x2 = w - margin + int(12 * s)
        bg_y2 = int(h * 0.87)
        self._blend_rect(canvas, bg_x1, bg_y1, bg_x2, bg_y2, alpha=0.25)

        # ===== 右上：角度3つ（横並び） =====
        cx1 = block_x0 + r
        cx2 = cx1 + (2 * r) + gap
        cx3 = cx2 + (2 * r) + gap
        self._circle_label(canvas, (cx1, row1_y), r, "ROLL",  None if roll  is None else int(roll),  0.50 * s)
        self._circle_label(canvas, (cx2, row1_y), r, "PITCH", None if pitch is None else int(pitch), 0.50 * s)
        self._circle_label(canvas, (cx3, row1_y), r, "YAW",   None if yaw   is None else int(yaw),   0.50 * s)

        # ===== 右上：加速度3つ（横並び） =====
        # 画像は「加速度」×3に見えるので、見た目は同じにして値だけ変える
        self._circle_label(canvas, (cx1, row2_y), r, "ACC", None if agx is None else int(agx), 0.55 * s)
        self._circle_label(canvas, (cx2, row2_y), r, "ACC", None if agy is None else int(agy), 0.55 * s)
        self._circle_label(canvas, (cx3, row2_y), r, "ACC", None if agz is None else int(agz), 0.55 * s)

        # ===== 右側：縦バー3本（ALT / SPD / BAT） =====
        bar_top = row2_y + r + int(28 * s)
        bar_h = int(120 * s)
        bar_h = max(80, min(bar_h, int(h * 0.35)))
        bar_w = int(30 * s)
        bar_w = max(22, min(bar_w, 42))

        bx1 = cx1 - bar_w // 2
        bx2 = cx2 - bar_w // 2
        bx3 = cx3 - bar_w // 2

        # 値→割合（適当にでも動くようにデフォルトレンジを置く）
        # 高度：0〜300cm を 0〜1 に（必要なら変えてOK）
        alt_ratio = None
        if height is not None:
            alt_ratio = max(0.0, min(1.0, float(height) / 300.0))

        # 速度：0〜100 を 0〜1 に（speed が無ければ None）
        spd_ratio = None
        if speed is not None:
            spd_ratio = max(0.0, min(1.0, float(speed) / 100.0))

        # バッテリー：0〜100%
        bat_ratio = None
        if battery is not None:
            bat_ratio = max(0.0, min(1.0, float(battery) / 100.0))

        self._bar(canvas, bx1, bar_top, bar_w, bar_h, alt_ratio)
        self._bar(canvas, bx2, bar_top, bar_w, bar_h, spd_ratio)
        self._bar(canvas, bx3, bar_top, bar_w, bar_h, bat_ratio)

        # ラベル（下）
        label_y = bar_top + bar_h + int(24 * s)

        alt_txt = f"ALT {int(height)}cm" if height is not None else "ALT --"
        spd_txt = f"SPD {int(speed)}" if speed is not None else "SPD --"
        bat_txt = f"BAT:{int(battery)}%" if battery is not None else "BAT:--%"

        self._put(canvas, alt_txt, (bx1 - int(18 * s), label_y), 0.55 * s, TEXT, 1)
        self._put(canvas, spd_txt, (bx2 - int(18 * s), label_y), 0.55 * s, TEXT, 1)
        self._put(canvas, bat_txt, (bx3 - int(18 * s), label_y), 0.55 * s, TEXT, 1)

        # ===== 右下：wifi強度 =====
        wifi_txt = f"wifi:{wifi if wifi is not None else '--'}"
        self._put_right(canvas, wifi_txt, int(w - 14 * s), int(h - 14 * s), 0.6 * s, TEXT, 1)

        # ===== 左下：コマンド表示 =====
        if commands is None:
            commands = "cmd: [T]takeoff [G]land [WASD]move [R/F]up/down [E/X]yaw [Z]quit"
        self._blend_rect(canvas, 0, int(h - 46 * s), int(w * 0.70), h, alpha=0.35)
        self._put(canvas, commands, (int(14 * s), int(h - 16 * s)), 0.55 * s, TEXT, 1)

        return canvas
