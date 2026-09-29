# surf_game/main.py
import pygame
import numpy as np
from queue import Queue, Empty

from config import (
    SERIAL_PORT,
    BAUDRATE,
    FPS,
    WINDOWED_SIZE,
)
from serial_backend import SerialReceiver
from pressure_analyzer import PressureAnalyzer
from game_engine import GameEngine
from renderer import Renderer


class SmartSurfGame:
    def __init__(self):
        pygame.init()
        pygame.display.set_caption("智能坐垫高级冲浪小游戏 - Pygame")

        self.fullscreen = True
        self.screen = pygame.display.set_mode((0, 0), pygame.FULLSCREEN)
        self.clock = pygame.time.Clock()

        self.renderer = Renderer(self.screen)

        self.data_queue = Queue()
        self.status_queue = Queue()

        self.serial_receiver = SerialReceiver(
            port=SERIAL_PORT,
            baudrate=BAUDRATE,
            data_queue=self.data_queue,
            status_queue=self.status_queue
        )
        self.serial_receiver.start()

        self.analyzer = PressureAnalyzer()
        self.engine = GameEngine()

        self.current_matrix = np.zeros((16, 32), dtype=np.float32)

        # 变量名保留 corrected_matrix，避免修改 renderer.py
        # 但当前实际保存的是原始矩阵，不再是修正矩阵
        self.corrected_matrix = np.zeros((16, 32), dtype=np.float32)

        self.current_data = None

        self.serial_status = "● 等待串口连接"
        self.serial_ok = False

        self.control = {
            "steer": 0.0,
            "accelerate": 0.0,
            "center": {
                "valid": False,
                "cx": 15.5,
                "cy": 7.5,
                "norm_x": 0.0,
                "norm_y": 0.0,
            }
        }

        self.key_state = {
            "left": False,
            "right": False,
            "up": False,
            "down": False,
        }

    # ============================================================
    # 串口数据
    # ============================================================

    def read_serial_status(self):
        try:
            while True:
                status = self.status_queue.get_nowait()
                self.serial_status = status.get("text", self.serial_status)
                self.serial_ok = bool(status.get("ok", False))
        except Empty:
            pass

    def read_serial_data(self):
        latest_data = None

        try:
            while True:
                latest_data = self.data_queue.get_nowait()
        except Empty:
            pass

        if latest_data is None:
            return

        self.current_data = latest_data
        self.current_matrix = latest_data["matrix"]

        # ========================================================
        # 图像显示：完全使用原始矩阵
        # 不再调用 self.analyzer.correct_matrix()
        # ========================================================
        self.corrected_matrix = self.current_matrix

        # ========================================================
        # 控制逻辑：也完全使用原始矩阵
        # PressureAnalyzer 内部已经不再做矩阵修正
        # ========================================================
        self.control = self.analyzer.matrix_to_control(
            self.current_matrix,
            is_seated=latest_data.get("is_seated", False)
        )

        self.control["posture_code"] = latest_data.get("posture_code", None)
        self.control["posture_name"] = latest_data.get("posture_name", "--")
        self.control["button_flag"] = latest_data.get("button_flag", 0)

    # ============================================================
    # 键盘控制
    # ============================================================

    def get_keyboard_control(self):
        steer = 0.0
        accel = 0.0

        if self.key_state["left"]:
            steer -= 1.0

        if self.key_state["right"]:
            steer += 1.0

        if self.key_state["up"]:
            accel += 1.0

        if self.key_state["down"]:
            accel -= 1.0

        return {
            "steer": steer,
            "accelerate": accel,
            "center": self.control.get("center", {})
        }

    def update_control_from_keyboard_if_needed(self):
        """
        有键盘输入时，优先用键盘。
        没有串口数据或离座时，也允许键盘调试。
        """
        key_control = self.get_keyboard_control()

        if abs(key_control["steer"]) > 0.01 or abs(key_control["accelerate"]) > 0.01:
            self.control = key_control
            return

        if self.current_data is None:
            self.control = key_control
            return

        if not self.current_data.get("is_seated", False):
            self.control = key_control

    # ============================================================
    # 事件
    # ============================================================

    def toggle_fullscreen(self):
        self.fullscreen = not self.fullscreen

        if self.fullscreen:
            self.screen = pygame.display.set_mode((0, 0), pygame.FULLSCREEN)
        else:
            self.screen = pygame.display.set_mode(WINDOWED_SIZE, pygame.RESIZABLE)

        self.renderer.update_screen(self.screen)

    def handle_events(self):
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return False

            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    return False

                elif event.key == pygame.K_SPACE:
                    self.engine.start()

                elif event.key == pygame.K_F11:
                    self.toggle_fullscreen()

                elif event.key == pygame.K_c:
                    # 校准也基于原始矩阵
                    ok = self.analyzer.calibrate(self.current_matrix)

                    if ok:
                        self.serial_status = "● 已校准当前坐姿为中心"
                        self.serial_ok = True
                    else:
                        self.serial_status = "● 校准失败，请确认已经坐下"
                        self.serial_ok = False

                elif event.key in (pygame.K_LEFT, pygame.K_a):
                    self.key_state["left"] = True

                elif event.key in (pygame.K_RIGHT, pygame.K_d):
                    self.key_state["right"] = True

                elif event.key in (pygame.K_UP, pygame.K_w):
                    self.key_state["up"] = True

                elif event.key in (pygame.K_DOWN, pygame.K_s):
                    self.key_state["down"] = True

            elif event.type == pygame.KEYUP:
                if event.key in (pygame.K_LEFT, pygame.K_a):
                    self.key_state["left"] = False

                elif event.key in (pygame.K_RIGHT, pygame.K_d):
                    self.key_state["right"] = False

                elif event.key in (pygame.K_UP, pygame.K_w):
                    self.key_state["up"] = False

                elif event.key in (pygame.K_DOWN, pygame.K_s):
                    self.key_state["down"] = False

            elif event.type == pygame.VIDEORESIZE:
                if not self.fullscreen:
                    self.screen = pygame.display.set_mode(event.size, pygame.RESIZABLE)
                    self.renderer.update_screen(self.screen)

        return True

    # ============================================================
    # 主循环
    # ============================================================

    def run(self):
        running = True

        while running:
            dt = self.clock.tick(FPS) / 1000.0
            dt = min(dt, 0.04)

            running = self.handle_events()

            self.read_serial_status()
            self.read_serial_data()
            self.update_control_from_keyboard_if_needed()

            self.engine.update(dt, self.control)

            self.renderer.draw(
                engine=self.engine,
                control=self.control,
                corrected_matrix=self.corrected_matrix,
                current_data=self.current_data,
                serial_status=self.serial_status,
                serial_ok=self.serial_ok
            )

        self.shutdown()

    def shutdown(self):
        try:
            self.serial_receiver.stop()
        except Exception:
            pass

        pygame.quit()


if __name__ == "__main__":
    app = SmartSurfGame()
    app.run()