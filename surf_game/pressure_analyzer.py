# surf_game/pressure_analyzer.py
import math
import numpy as np

from config import (
    STEER_SENSITIVITY,
    ACCEL_SENSITIVITY,
    DEAD_ZONE_X,
    DEAD_ZONE_Y,
    CONTROL_SMOOTH_ALPHA,
)


class PressureAnalyzer:
    """
    压力矩阵分析模块。

    当前版本说明：
    1. 游戏控制完全使用原始 16×32 压力矩阵。
    2. 不再做任何行顺序修正。
    3. correct_matrix() 函数保留，但只做格式检查，不做重排。
    4. 左右倾控制 steer。
    5. 前后倾控制 accelerate。
    6. 已按要求反转前后倾逻辑：accel = norm_y。
    """

    def __init__(self):
        self.rows = 16
        self.cols = 32

        self.dead_zone_x = DEAD_ZONE_X
        self.dead_zone_y = DEAD_ZONE_Y

        self.calibrated = False
        self.calib_cx = 15.5
        self.calib_cy = 7.5

        self.smooth_steer = 0.0
        self.smooth_accel = 0.0

        self.alpha = CONTROL_SMOOTH_ALPHA

    def correct_matrix(self, matrix):
        """
        保留函数名，避免其他模块大量改动。

        现在不再做图像/控制修正：
        - 不使用 row_correct_index
        - 不改变行顺序
        - 不改变列顺序
        - 只检查矩阵格式

        返回：
        - 若输入合法，返回原始矩阵的 float32 副本
        - 若输入非法，返回 16×32 零矩阵
        """
        if matrix is None:
            return np.zeros((16, 32), dtype=np.float32)

        matrix = np.asarray(matrix, dtype=np.float32)

        if matrix.shape != (16, 32):
            return np.zeros((16, 32), dtype=np.float32)

        return matrix

    def compute_center(self, matrix, use_calibration=True):
        """
        计算压力中心。

        输入 matrix 已经是原始矩阵，不做行修正。
        """
        matrix = np.asarray(matrix, dtype=np.float32)

        if matrix.shape != (16, 32):
            return {
                "valid": False,
                "cx": 15.5,
                "cy": 7.5,
                "norm_x": 0.0,
                "norm_y": 0.0,
                "total": 0.0,
            }

        total = float(np.sum(matrix))

        if total <= 1:
            return {
                "valid": False,
                "cx": 15.5,
                "cy": 7.5,
                "norm_x": 0.0,
                "norm_y": 0.0,
                "total": total,
            }

        y_indices, x_indices = np.indices(matrix.shape)

        cx = float(np.sum(x_indices * matrix) / total)
        cy = float(np.sum(y_indices * matrix) / total)

        if use_calibration and self.calibrated:
            range_x = max(1.0, max(self.calib_cx, 31 - self.calib_cx))
            range_y = max(1.0, max(self.calib_cy, 15 - self.calib_cy))

            norm_x = (cx - self.calib_cx) / range_x
            norm_y = (cy - self.calib_cy) / range_y
        else:
            norm_x = (cx - 15.5) / 15.5
            norm_y = (cy - 7.5) / 7.5

        norm_x = float(np.clip(norm_x, -1.0, 1.0))
        norm_y = float(np.clip(norm_y, -1.0, 1.0))

        return {
            "valid": True,
            "cx": cx,
            "cy": cy,
            "norm_x": norm_x,
            "norm_y": norm_y,
            "total": total,
        }

    def calibrate(self, matrix):
        """
        校准当前坐姿中心。

        注意：
        现在校准也基于原始矩阵，不做行修正。
        """
        raw_matrix = self.correct_matrix(matrix)
        center = self.compute_center(raw_matrix, use_calibration=False)

        if center["valid"]:
            self.calib_cx = center["cx"]
            self.calib_cy = center["cy"]
            self.calibrated = True

            self.smooth_steer = 0.0
            self.smooth_accel = 0.0

            return True

        return False

    def _curve(self, value, power=1.12):
        """
        非线性控制曲线。

        power 略大于 1：
        小动作更稳，大动作仍然有效。
        """
        if abs(value) < 1e-6:
            return 0.0

        return float(math.copysign(abs(value) ** power, value))

    def matrix_to_control(self, matrix, is_seated=True):
        """
        将原始压力矩阵转换为游戏控制量。

        返回：
        steer:
            < 0 左转
            > 0 右转

        accelerate:
            > 0 加速
            < 0 减速/后倾停车

        当前版本：
        - 完全不做矩阵修正
        - 直接使用串口收到的原始 16×32 矩阵
        """
        if not is_seated:
            self.smooth_steer *= 0.86
            self.smooth_accel *= 0.86

            return {
                "steer": 0.0,
                "accelerate": 0.0,
                "center": {
                    "valid": False,
                    "cx": 15.5,
                    "cy": 7.5,
                    "norm_x": 0.0,
                    "norm_y": 0.0,
                    "total": 0.0,
                }
            }

        raw_matrix = self.correct_matrix(matrix)
        center = self.compute_center(raw_matrix)

        norm_x = center["norm_x"]
        norm_y = center["norm_y"]

        # ========================================================
        # 左右倾斜控制
        # ========================================================
        if abs(norm_x) < self.dead_zone_x:
            steer = 0.0
        else:
            steer = norm_x

        # ========================================================
        # 前后倾斜控制
        # ========================================================
        # 已按你的要求反转：
        # 原来是 accel = -norm_y
        # 现在是 accel = norm_y
        if abs(norm_y) < self.dead_zone_y:
            accel = 0.0
        else:
            accel = norm_y

        steer = self._curve(steer) * STEER_SENSITIVITY
        accel = self._curve(accel) * ACCEL_SENSITIVITY

        steer = float(np.clip(steer, -1.0, 1.0))
        accel = float(np.clip(accel, -1.0, 1.0))

        self.smooth_steer = (
            self.smooth_steer * (1 - self.alpha)
            + steer * self.alpha
        )

        self.smooth_accel = (
            self.smooth_accel * (1 - self.alpha)
            + accel * self.alpha
        )

        return {
            "steer": float(np.clip(self.smooth_steer, -1.0, 1.0)),
            "accelerate": float(np.clip(self.smooth_accel, -1.0, 1.0)),
            "center": center,
        }