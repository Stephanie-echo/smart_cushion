# surf_game/config.py
import os

# ============================================================
# 串口配置
# 优先使用 UI 通过环境变量传入的串口号和波特率
# 如果没有环境变量，则默认 COM18 / 460800
# ============================================================

SERIAL_PORT = os.environ.get("SMART_CUSHION_PORT", "COM18")

try:
    BAUDRATE = int(os.environ.get("SMART_CUSHION_BAUDRATE", "460800"))
except ValueError:
    BAUDRATE = 460800


FPS = 60
WINDOWED_SIZE = (1400, 850)

TARGET_COINS = 30

SEATED_PEAK_THRESHOLD = 300

# ============================================================
# 控制灵敏度
# ============================================================

STEER_SENSITIVITY = 1.65
ACCEL_SENSITIVITY = 1.35

DEAD_ZONE_X = 0.065
DEAD_ZONE_Y = 0.065

CONTROL_SMOOTH_ALPHA = 0.24

# ============================================================
# 运动参数
# ============================================================

BASE_SPEED = 210
MAX_SPEED = 620
ACCEL_RATE = 760

BACK_STOP_THRESHOLD = -0.16

NATURAL_DRAG = 0.988
TURN_RATE = 2.8

# 方向限制：只能在初始前方 180 度范围内旋转
MAX_HEADING_ANGLE = 1.57079632679

# ============================================================
# 画面显示
# ============================================================

VIEW_SCALE = 0.78
PLAYER_DRAW_SCALE = 0.72

POSTURE_MAP = {
    0: "端坐",
    1: "前倾",
    2: "后倾",
    3: "左倾",
    4: "右倾",
    5: "左腿离地二郎腿",
    6: "右腿离地二郎腿",
    7: "离座",
}