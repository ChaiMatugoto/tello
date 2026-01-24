# tello_controller.py
import time
import numpy as np
from djitellopy import Tello
from keyboard_state import KeyboardState


def clamp_int(x, lo, hi):
    return int(max(lo, min(hi, x)))


class TelloController:
    """
    send_rc_control(lr, fb, ud, yaw)
      lr : +右
      fb : +前
      ud : +上
      yaw: +時計回り
    """

    def __init__(self, keyboard_state: KeyboardState):
        self.tello = Tello()
        self.in_flight = False
        self.frame_read = None
        self.kb = keyboard_state

        # RC（送信用の意味で固定）
        self.lr = 0
        self.fb = 0
        self.ud = 0
        self.yaw = 0

        # 手動速度
        self.speed = 60
        self.precise_div = 3

        # ---- セミオート ----
        self.approach_enabled = False
        self.target_aruco_id = None

        # 中心合わせ（px）
        self.center_dead_px = 14
        self.k_err_to_lr = 0.18     # ★中心ズレは lr で直す（近距離で安定）
        self.lr_max = 35

        # yaw（中心補助）
        self.k_err_to_yaw = 0.25    # ★中心err_x→yawは弱め（暴走防止）
        self.yaw_max = 60
        self.inv_yaw = False        # 右のマーカーへ向けて回らないなら True

        # 正面（角度）合わせ：skew（台形歪み）
        self.skew_dead = 0.07
        self.k_skew_to_yaw = 200    # 120〜260くらいで調整

        # 距離（size_px）
        self.target_size_px = 220
        self.size_dead_px = 12
        self.k_size_to_fb = 0.25
        self.fb_max = 35
        self.fb_min = 10

        # 見失い停止
        self.last_marker_ts = 0.0
        self.lost_stop_sec = 0.4

        # 近距離ほど yaw を弱める
        self.near_ratio = 0.85  # target_size_px * 0.85 以上で「近い」扱い

        # smoothing（少しだけ）
        self.smooth = 0.35
        self._yaw_f = 0.0
        self._fb_f = 0.0
        self._lr_f = 0.0

        # ---- UI / debug ----
        self.approach_state = "OFF"
        self.approach_err_x = None
        self.approach_size_px = None
        self.approach_skew = None
        self.approach_yaw = 0
        self.approach_fb = 0
        self.approach_lr = 0

    # -----------------------
    # connect / frame
    # -----------------------
    def connect_and_start_stream(self):
        self.tello.connect()
        print(f"Battery: {self.tello.get_battery()}%")
        self.tello.streamon()
        self.frame_read = self.tello.get_frame_read()

    def get_frame(self):
        if self.frame_read is None or self.frame_read.frame is None:
            return np.zeros((480, 640, 3), dtype=np.uint8)
        return self.frame_read.frame[:, :, ::-1]  # RGB->BGR

    # -----------------------
    # keys
    # -----------------------
    def handle_key(self, key):
        if key == ord('z'):
            return True

        if key == ord('t'):
            try:
                b = self.tello.get_battery()
                if b < 20:
                    print("Battery too low for takeoff.")
                else:
                    self.tello.takeoff()
                    self.in_flight = True
                    self.stop_all()
            except Exception as e:
                print("Takeoff failed:", e)

        elif key == ord('g'):
            try:
                self.tello.land()
            except Exception as e:
                print("Land failed:", e)
            self.in_flight = False
            self.stop_all()

        elif key == ord('p'):
            self.approach_enabled = not self.approach_enabled
            print(f"[APPROACH] enabled={self.approach_enabled}")
            self.stop_all()
            self.approach_state = "ON" if self.approach_enabled else "OFF"

        return False

    def stop_all(self):
        self.lr = self.fb = self.ud = self.yaw = 0
        self._yaw_f = self._fb_f = self._lr_f = 0.0
        self.approach_yaw = 0
        self.approach_fb = 0
        self.approach_lr = 0

    # -----------------------
    # manual
    # -----------------------
    def manual_active(self):
        if not self.in_flight:
            return False
        keys = ['w', 'a', 's', 'd', 'r', 'f', 'q', 'e', 'space', 'shift']
        return any(self.kb.is_pressed(k) for k in keys)

    def update_motion_from_keyboard(self):
        """
        ★今あなたが動いてる割当を維持（今のあなたのコードのまま）
          w/s = 前後
          d/a = 左右
        """
        if not self.in_flight:
            return

        lr = fb = ud = yw = 0
        speed = self.speed
        if self.kb.is_pressed('shift'):
            speed = max(15, self.speed // self.precise_div)

        # 前後（fb）
        if self.kb.is_pressed('w'):
            fb += speed
        if self.kb.is_pressed('s'):
            fb -= speed

        # 左右（lr）
        if self.kb.is_pressed('d'):
            lr += speed
        if self.kb.is_pressed('a'):
            lr -= speed

        # 上下（ud）
        if self.kb.is_pressed('r'):
            ud += speed
        if self.kb.is_pressed('f'):
            ud -= speed

        # yaw
        if self.kb.is_pressed('e'):
            yw += speed
        if self.kb.is_pressed('q'):
            yw -= speed

        if self.kb.is_pressed('space'):
            lr = fb = ud = yw = 0

        self.lr, self.fb, self.ud, self.yaw = lr, fb, ud, yw

    # -----------------------
    # semi-auto（中心＋正面＋距離）
    # -----------------------
    def update_approach_from_aruco(self, marker_info, frame_shape):
        if not self.in_flight:
            return
        if not self.approach_enabled:
            self.approach_state = "OFF"
            return

        # 手動なら上書きしない
        if self.manual_active():
            self.approach_state = "MANUAL"
            return

        now = time.time()

        # 見失い
        if marker_info is None:
            if (now - self.last_marker_ts) > self.lost_stop_sec:
                self.stop_all()
            self.approach_state = "NO_MARKER"
            self.approach_err_x = None
            self.approach_size_px = None
            self.approach_skew = None
            self.approach_yaw = 0
            self.approach_fb = 0
            self.approach_lr = 0
            return

        self.last_marker_ts = now

        h, w = frame_shape[:2]
        cx, cy = marker_info["center"]
        size_px = float(marker_info["size_px"])
        err_x = float(cx - (w / 2.0))  # +右

        self.approach_err_x = err_x
        self.approach_size_px = size_px

        # ---- skew（正面度） ----
        skew = None
        yaw_from_skew = 0.0
        quad = marker_info.get("corners", None)
        if quad is not None:
            q = np.array(quad, dtype=np.float32).reshape(4, 2)
            tl, tr, br, bl = q[0], q[1], q[2], q[3]
            left_len = float(np.linalg.norm(bl - tl))
            right_len = float(np.linalg.norm(br - tr))
            denom = max(1e-6, left_len + right_len)
            skew = (right_len - left_len) / denom
            if abs(skew) > self.skew_dead:
                yaw_from_skew = self.k_skew_to_yaw * skew
        self.approach_skew = skew

        # ---- 近距離スケール（yawを弱める） ----
        ratio = min(1.5, max(0.0, size_px / float(self.target_size_px)))
        yaw_scale = max(0.25, 1.0 - (ratio - 0.6))

        # ---- (1) 中心合わせ：lr主役 ----
        lr_cmd = 0.0
        if abs(err_x) > self.center_dead_px:
            lr_cmd = self.k_err_to_lr * err_x
        lr_cmd = clamp_int(lr_cmd, -self.lr_max, self.lr_max)

        # ---- (2) yaw：中心補助は遠い時だけ少し + skewは常に ----
        yaw_from_center = 0.0
        if size_px < (self.target_size_px * self.near_ratio):
            if abs(err_x) > self.center_dead_px:
                yaw_from_center = self.k_err_to_yaw * err_x

        yaw_cmd = (yaw_from_center + yaw_from_skew) * yaw_scale
        yaw_cmd = clamp_int(yaw_cmd, -self.yaw_max, self.yaw_max)
        if self.inv_yaw:
            yaw_cmd = -yaw_cmd

        # ---- (3) 前進：sizeで距離 ----
        size_err = self.target_size_px - size_px  # +遠い
        fb_cmd = 0.0
        if abs(size_err) > self.size_dead_px:
            fb_cmd = self.k_size_to_fb * size_err
            fb_cmd = clamp_int(fb_cmd, -self.fb_max, self.fb_max)
            if fb_cmd > 0:
                fb_cmd = max(self.fb_min, fb_cmd)

        # ズレてる間は前進抑制
        not_centered = abs(err_x) > self.center_dead_px
        not_facing = (skew is not None and abs(skew) > self.skew_dead)
        if (not_centered or not_facing) and fb_cmd > 0:
            fb_cmd = int(fb_cmd * 0.45)

        # smoothing
        a = self.smooth
        self._yaw_f = a * self._yaw_f + (1 - a) * yaw_cmd
        self._fb_f  = a * self._fb_f  + (1 - a) * fb_cmd
        self._lr_f  = a * self._lr_f  + (1 - a) * lr_cmd

        yaw_cmd = int(round(self._yaw_f))
        fb_cmd  = int(round(self._fb_f))
        lr_cmd  = int(round(self._lr_f))

        # state
        if skew is not None and abs(skew) > self.skew_dead:
            self.approach_state = "FACING"
        elif abs(err_x) > self.center_dead_px:
            self.approach_state = "CENTERING"
        elif fb_cmd > 0:
            self.approach_state = "APPROACH"
        else:
            self.approach_state = "HOLD"

        # ★セミオート適用
        self.lr = lr_cmd
        self.fb = fb_cmd
        self.ud = 0
        self.yaw = yaw_cmd

        # UI
        self.approach_yaw = yaw_cmd
        self.approach_fb = fb_cmd
        self.approach_lr = lr_cmd

    # -----------------------
    # send rc
    # -----------------------
    def update_motion(self):
        if not self.in_flight:
            return
        lr = clamp_int(self.lr, -100, 100)
        fb = clamp_int(self.fb, -100, 100)
        ud = clamp_int(self.ud, -100, 100)
        yw = clamp_int(self.yaw, -100, 100)

        # debug（0.2秒に1回）
        if not hasattr(self, "_dbg_t"):
            self._dbg_t = 0.0
        now = time.time()
        if now - self._dbg_t > 0.2:
            self._dbg_t = now
            print(f"[RC DBG] lr={lr} fb={fb} ud={ud} yaw={yw}  approach={self.approach_enabled} "
                  f"state={self.approach_state} err_x={self.approach_err_x} size={self.approach_size_px} skew={self.approach_skew}")

        try:
            self.tello.send_rc_control(lr, fb, ud, yw)
        except Exception as e:
            print("send_rc_control failed:", e)

    def cleanup(self):
        try:
            self.tello.streamoff()
        except Exception:
            pass
        if self.in_flight:
            try:
                self.tello.land()
            except Exception:
                pass
        self.tello.end()
