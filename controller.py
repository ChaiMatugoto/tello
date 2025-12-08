import time
import cv2
import numpy as np
from djitellopy import Tello


def main():
    tello = Tello()
    tello.connect()
    print(f"Battery: {tello.get_battery()}%")

    # 映像ストリームを開始してウィンドウで表示（任意）
    try:
        tello.streamon()
        frame_read = tello.get_frame_read()
    except Exception:
        frame_read = None

    # 移動量（cm）・回転角（度）
    MOVE_DIST = 30
    ROTATE_DEG = 30

    print("Controls: t=takeoff, g=land, w/a/s/d move, r/f up/down, e/x yaw right/left, z=quit")

    # 安全状態トラッキング
    in_flight = False

    while True:
        # フレーム表示（あれば）
        if frame_read is not None:
            frame = frame_read.frame
            if frame is None:
                frame = 255 * np.ones((480, 640, 3), dtype=np.uint8)
        else:
            frame = 255 * np.ones((480, 640, 3), dtype=np.uint8)

        frame = cv2.resize(frame, (640, 480))
        cv2.imshow("tello", frame)

        key = cv2.waitKey(1) & 0xFF
        if key == ord('z'):
            print("Exiting loop")
            break
        elif key == ord('t'):
            print("Takeoff requested")
            try:
                battery = tello.get_battery()
                print(f"Battery before takeoff check: {battery}%")
                if battery < 20:
                    print("Battery too low for takeoff (requires >=20%). Charge battery and retry.")
                else:
                    tello.takeoff()
                    in_flight = True
            except Exception as e:
                print(f"Takeoff failed: {e}")
        elif key == ord('g'):
            print("Land requested")
            try:
                tello.land()
            except Exception as e:
                print(f"Land failed: {e}")
            in_flight = False
        elif key == ord('w'):
            print("Forward")
            tello.move_forward(MOVE_DIST)
        elif key == ord('s'):
            print("Backward")
            tello.move_back(MOVE_DIST)
        elif key == ord('a'):
            print("Left")
            tello.move_left(MOVE_DIST)
        elif key == ord('d'):
            print("Right")
            tello.move_right(MOVE_DIST)
        elif key == ord('r'):
            print("Up")
            tello.move_up(MOVE_DIST)
        elif key == ord('f'):
            print("Down")
            tello.move_down(MOVE_DIST)
        elif key == ord('e'):
            print("Yaw right")
            tello.rotate_clockwise(ROTATE_DEG)
        elif key == ord('x'):
            print("Yaw left")
            tello.rotate_counter_clockwise(ROTATE_DEG)

    # 終了処理
    try:
        tello.streamoff()
    except Exception:
        pass
    cv2.destroyAllWindows()
    # プログラム終了時にまだ飛んでいる場合は着陸を試みる
    if in_flight:
        try:
            print("Attempting emergency land before exit")
            tello.land()
        except Exception as e:
            print(f"Emergency land failed: {e}")

    tello.end()


if __name__ == "__main__":
    main()
