# tello_controller.py
import cv2
import numpy as np
from djitellopy import Tello


class TelloController:
    """Telloの接続・映像取得・キー操作をまとめるクラス"""

    def __init__(self):
        self.tello = Tello()
        self.in_flight = False
        self.frame_read = None

        # ここがポイント：現在の速度を状態として持つ
        self.vx = 0  # 前後
        self.vy = 0  # 左右
        self.vz = 0  # 上下
        self.yaw = 0  # 回転

        # 速度の大きさ（-100〜100の範囲で使う）
        self.speed = 40

    def connect_and_start_stream(self):
        """Telloに接続して映像ストリーム開始"""
        self.tello.connect()
        print(f"Battery: {self.tello.get_battery()}%")
        self.tello.streamon()
        self.frame_read = self.tello.get_frame_read()

    def get_frame(self, size=(640, 480)):
        """現在のフレームを取得してリサイズして返す"""
        if self.frame_read is None:
            return 255 * np.ones((size[1], size[0], 3), dtype=np.uint8)

        frame = self.frame_read.frame
        if frame is None:
            return 255 * np.ones((size[1], size[0], 3), dtype=np.uint8)

        return cv2.resize(frame, size)

    def handle_key(self, key):
        """
        キー入力に応じてTelloを操作する。
        戻り値: True を返したらメインループ終了。
        """

        # ===== 終了 =====
        if key == ord('z'):
            print("Exiting loop")
            return True

        # ===== 離陸・着陸 =====
        elif key == ord('t'):
            print("Takeoff requested")
            try:
                battery = self.tello.get_battery()
                print(f"Battery before takeoff check: {battery}%")
                if battery < 20:
                    print("Battery too low for takeoff (requires >=20%). Charge battery and retry.")
                else:
                    self.tello.takeoff()
                    self.in_flight = True

                    # 離陸直後は速度ゼロからスタート
                    self.vx = self.vy = self.vz = self.yaw = 0
            except Exception as e:
                print(f"Takeoff failed: {e}")

        elif key == ord('g'):
            print("Land requested")
            try:
                self.tello.land()
            except Exception as e:
                print(f"Land failed: {e}")
            self.in_flight = False
            self.vx = self.vy = self.vz = self.yaw = 0

        # ===== ここから移動系：速度を変えるだけ =====

        # 前後
        elif key == ord('w'):
            print("Set: forward")
            self.vx = self.speed
        elif key == ord('s'):
            print("Set: backward")
            self.vx = -self.speed

        # 左右
        elif key == ord('a'):
            print("Set: left")
            self.vy = -self.speed
        elif key == ord('d'):
            print("Set: right")
            self.vy = self.speed

        # 上下
        elif key == ord('r'):
            print("Set: up")
            self.vz = self.speed
        elif key == ord('f'):
            print("Set: down")
            self.vz = -self.speed

        # 回転
        elif key == ord('e'):
            print("Set: yaw right")
            self.yaw = self.speed
        elif key == ord('x'):
            print("Set: yaw left")
            self.yaw = -self.speed

        # スペースキーで完全停止
        elif key == ord(' '):
            print("Stop all motion")
            self.vx = self.vy = self.vz = self.yaw = 0

        return False  # まだ終わらない

    def update_motion(self):
        """現在の速度(vx,vy,vz,yaw)をTelloに送る（毎フレーム呼ぶ）"""
        if not self.in_flight:
            return

        try:
            self.tello.send_rc_control(self.vx, self.vy, self.vz, self.yaw)
        except Exception as e:
            print(f"send_rc_control failed: {e}")

    def cleanup(self):
        """ストリーム停止・緊急着陸などの後片付け"""
        try:
            self.tello.streamoff()
        except Exception:
            pass

        if self.in_flight:
            try:
                print("Attempting emergency land before exit")
                self.tello.land()
            except Exception as e:
                print(f"Emergency land failed: {e}")

        self.tello.end()
