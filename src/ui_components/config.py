# ui_components/config.py
"""
UIの「よく調整する数値」をここに集約。
見た目調整は基本このファイルだけ触ればOK。
"""

# ===== 共通スケール =====
# drone_ui.py 側で s = clamp(w/900) を作って、最終的に「係数 * s * ts」で文字サイズが決まる
S_MIN = 0.6
S_MAX = 1.10
S_BASE_W = 900.0

# ===== 左HUD（映像側） =====
HUD_SN_X = 14
HUD_SN_Y = 38
HUD_SN_SCALE = 0.62
HUD_SN_ALPHA = 0.20

HUD_TOP_RIGHT_PAD_X = 14
HUD_TOP_Y = 36
HUD_TOP_PAD = 10
HUD_TOP_SCALE = 0.68
HUD_TOP_ALPHA = 0.18

HUD_WIFI_RIGHT_INSET = 230
HUD_WIFI_BOTTOM_INSET = 14
HUD_WIFI_SCALE = 0.60
HUD_WIFI_ALPHA = 0.14

HUD_CMD_X = 14
HUD_CMD_BOTTOM_INSET = 22
HUD_CMD_PAD = 10
HUD_CMD_SCALE = 0.56
HUD_CMD_ALPHA = 0.16

# ===== 右パネル（メーター/バー） =====
PANEL_COLS = 2
PANEL_ROWS = 3

PANEL_MARGIN = 10
GAUGE_GAP_X = 18
GAUGE_GAP_Y = 75

PANEL_BLOCK_TOP = 18
PANEL_BOTTOM_RESERVED = 180  # 下にバー/ラベル分を確保（大きいほどメーターが小さくなる）

GAUGE_MIN_R = 28

GAUGE_BG_PAD_X = 12
GAUGE_BG_PAD_TOP = 16
GAUGE_BG_PAD_BOTTOM = 20
GAUGE_BG_ALPHA = 0.12

# メーター ↔ バー間隔
GAUGE_TO_BAR_GAP = 105

# バー
BAR_GAP = 60
BAR_MIN_W = 5

BAR_LABEL_SPACE = 70   # バー下にラベル領域を確保
BAR_BOTTOM_PAD = 18    # パネル下との余白（小さくすると詰められる）

BAR_H_RATIO = 0.20     # hに対するバー高さ比
BAR_MIN_H = 80         # バー最低高さ

# バーラベル
BAR_LABEL_SCALE = 0.56
BAR_LABEL_Y_GAP = 22   # バー下端 ↔ ラベル開始の距離（重なるならここを増やす）
BAR_LABEL_PAD = 6
BAR_LABEL_ALPHA = 0.14
