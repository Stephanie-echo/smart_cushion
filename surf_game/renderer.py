# renderer.py
import math
import time
import random

import pygame
import numpy as np

from config import VIEW_SCALE, PLAYER_DRAW_SCALE
from utils import clamp, draw_text, value_to_rgb


class Renderer:
    """
    Pygame 绘制模块。

    本版修改：
    1. 地图整体显示缩小 VIEW_SCALE，能看到更大范围。
    2. 人物绘制缩小 PLAYER_DRAW_SCALE。
    3. 金币、障碍、水花也按 VIEW_SCALE 缩放。
    """

    def __init__(self, screen):
        self.screen = screen
        self.update_screen_size()

        self.font_big = pygame.font.SysFont("microsoftyahei", 48, bold=True)
        self.font_mid = pygame.font.SysFont("microsoftyahei", 28, bold=True)
        self.font = pygame.font.SysFont("microsoftyahei", 22)
        self.font_small = pygame.font.SysFont("microsoftyahei", 16)

    def update_screen(self, screen):
        self.screen = screen
        self.update_screen_size()

    def update_screen_size(self):
        self.screen_w, self.screen_h = self.screen.get_size()

    def world_to_screen(self, engine, pos):
        center = pygame.Vector2(self.screen_w / 2, self.screen_h / 2)
        return center + (pos - engine.camera_pos) * VIEW_SCALE

    def local_to_screen(self, center, heading, lx, ly):
        """
        人物局部坐标转屏幕坐标，并应用人物缩放。
        """
        s = PLAYER_DRAW_SCALE
        lx *= s
        ly *= s

        forward = pygame.Vector2(math.sin(heading), -math.cos(heading))
        right = pygame.Vector2(math.cos(heading), math.sin(heading))

        p = pygame.Vector2(center) + right * lx + forward * ly
        return int(p.x), int(p.y)

    def draw(
        self,
        engine,
        control,
        corrected_matrix,
        current_data,
        serial_status,
        serial_ok
    ):
        self.draw_background(engine)
        self.draw_world_elements(engine)
        self.draw_particles(engine)
        self.draw_player(engine, control)
        self.draw_float_texts(engine)
        self.draw_hud(engine, control, serial_status, serial_ok)
        self.draw_heatmap_panel(corrected_matrix, control, current_data)
        self.draw_flash(engine)
        self.draw_state_overlay(engine)

        pygame.display.flip()

    # ============================================================
    # 背景
    # ============================================================
    def draw_background(self, engine):
        self.screen.fill((56, 189, 248))

        pygame.draw.rect(
            self.screen,
            (14, 165, 233),
            (0, int(self.screen_h * 0.35), self.screen_w, self.screen_h)
        )

        pygame.draw.rect(
            self.screen,
            (2, 132, 199),
            (0, int(self.screen_h * 0.68), self.screen_w, self.screen_h)
        )

        # 世界坐标泡沫点，使用 VIEW_SCALE 后画面范围更大
        grid = 220
        cam_x = engine.camera_pos.x
        cam_y = engine.camera_pos.y

        world_half_w = self.screen_w / 2 / VIEW_SCALE
        world_half_h = self.screen_h / 2 / VIEW_SCALE

        start_x = int((cam_x - world_half_w) // grid * grid)
        end_x = int((cam_x + world_half_w) // grid * grid + grid)

        start_y = int((cam_y - world_half_h) // grid * grid)
        end_y = int((cam_y + world_half_h) // grid * grid + grid)

        for gx in range(start_x, end_x, grid):
            for gy in range(start_y, end_y, grid):
                seed = (gx * 928371 + gy * 123457) & 0xffffffff
                rnd = random.Random(seed)

                if rnd.random() < 0.6:
                    world = pygame.Vector2(
                        gx + rnd.uniform(20, grid - 20),
                        gy + rnd.uniform(20, grid - 20)
                    )

                    screen = self.world_to_screen(engine, world)

                    if -40 < screen.x < self.screen_w + 40 and -40 < screen.y < self.screen_h + 40:
                        r = int(rnd.uniform(2, 5) * VIEW_SCALE)
                        r = max(1, r)

                        pygame.draw.circle(
                            self.screen,
                            (224, 242, 254),
                            (int(screen.x), int(screen.y)),
                            r
                        )

        # 世界坐标波浪线
        wave_gap = 160
        base_y = int((cam_y - world_half_h) // wave_gap * wave_gap)

        for i in range(-2, int((world_half_h * 2) / wave_gap) + 4):
            world_y = base_y + i * wave_gap
            points = []

            for sx in range(-120, self.screen_w + 140, 36):
                wx = cam_x - world_half_w + sx / VIEW_SCALE
                world = pygame.Vector2(wx, world_y)

                p = self.world_to_screen(engine, world)
                sy = p.y + math.sin((wx + world_y * 0.3) * 0.018) * 12 * VIEW_SCALE

                points.append((sx, int(sy)))

            if len(points) >= 2:
                pygame.draw.lines(
                    self.screen,
                    (224, 242, 254),
                    False,
                    points,
                    max(1, int(3 * VIEW_SCALE))
                )

    # ============================================================
    # 世界元素
    # ============================================================
    def draw_world_elements(self, engine):
        self.draw_coins(engine)
        self.draw_obstacles(engine)

    def draw_coins(self, engine):
        for coin in engine.coins:
            screen = self.world_to_screen(engine, coin["pos"])

            if not (-100 < screen.x < self.screen_w + 100 and -100 < screen.y < self.screen_h + 100):
                continue

            pulse = math.sin(time.time() * 5 + coin["phase"]) * 3
            r = int((coin["radius"] + pulse) * VIEW_SCALE)
            r = max(6, r)

            pygame.draw.circle(self.screen, (250, 204, 21), screen, r)
            pygame.draw.circle(self.screen, (161, 98, 7), screen, r, max(2, int(3 * VIEW_SCALE)))

            pygame.draw.circle(
                self.screen,
                (254, 243, 199),
                (int(screen.x - r * 0.25), int(screen.y - r * 0.25)),
                max(3, r // 4)
            )

            draw_text(
                self.screen,
                self.font_small,
                "★",
                (screen.x, screen.y - 9),
                (255, 255, 255),
                center=True
            )

    def draw_obstacles(self, engine):
        for obs in engine.obstacles:
            screen = self.world_to_screen(engine, obs["pos"])

            if not (-160 < screen.x < self.screen_w + 160 and -160 < screen.y < self.screen_h + 160):
                continue

            r = int(obs["radius"] * VIEW_SCALE)
            r = max(12, r)

            kind = obs["kind"]

            if kind == "rock":
                pygame.draw.circle(self.screen, (100, 116, 139), screen, r)
                pygame.draw.circle(self.screen, (51, 65, 85), screen, r, max(2, int(4 * VIEW_SCALE)))

                pygame.draw.circle(
                    self.screen,
                    (148, 163, 184),
                    (int(screen.x - r * 0.25), int(screen.y - r * 0.25)),
                    int(r * 0.28)
                )

            elif kind == "buoy":
                pygame.draw.circle(self.screen, (239, 68, 68), screen, r)
                pygame.draw.circle(self.screen, (127, 29, 29), screen, r, max(2, int(4 * VIEW_SCALE)))

                pygame.draw.rect(
                    self.screen,
                    (255, 255, 255),
                    pygame.Rect(screen.x - r, screen.y - max(3, r * 0.18), r * 2, max(6, r * 0.36))
                )

            elif kind == "wood":
                rect = pygame.Rect(0, 0, int(r * 2.8), int(r * 0.9))
                rect.center = screen

                pygame.draw.rect(self.screen, (146, 64, 14), rect, border_radius=8)
                pygame.draw.rect(self.screen, (69, 26, 3), rect, max(2, int(4 * VIEW_SCALE)), border_radius=8)

                pygame.draw.line(
                    self.screen,
                    (251, 191, 36),
                    (rect.left + 10, rect.centery),
                    (rect.right - 10, rect.centery),
                    max(2, int(3 * VIEW_SCALE))
                )

            else:
                # 鲨鱼
                body = [
                    (screen.x - r * 1.25, screen.y),
                    (screen.x - r * 0.25, screen.y - r * 0.55),
                    (screen.x + r * 1.25, screen.y),
                    (screen.x - r * 0.25, screen.y + r * 0.55),
                ]

                pygame.draw.polygon(self.screen, (71, 85, 105), body)
                pygame.draw.polygon(self.screen, (30, 41, 59), body, max(2, int(3 * VIEW_SCALE)))

                fin = [
                    (screen.x - r * 0.1, screen.y - r * 0.25),
                    (screen.x + r * 0.15, screen.y - r * 1.0),
                    (screen.x + r * 0.32, screen.y - r * 0.15),
                ]

                pygame.draw.polygon(self.screen, (51, 65, 85), fin)

    # ============================================================
    # 粒子
    # ============================================================
    def draw_particles(self, engine):
        for p in engine.particles:
            screen = self.world_to_screen(engine, p["pos"])

            alpha = clamp(p["life"] / p["max_life"], 0, 1)
            r = int(p["radius"] * alpha * VIEW_SCALE)

            if r <= 0:
                continue

            pygame.draw.circle(
                self.screen,
                (224, 242, 254),
                (int(screen.x), int(screen.y)),
                r
            )

    # ============================================================
    # 人物
    # ============================================================
    def draw_player(self, engine, control):
        center = (self.screen_w // 2, self.screen_h // 2)

        if engine.invincible_timer > 0 and int(engine.invincible_timer * 12) % 2 == 0:
            return

        steer = float(control.get("steer", 0.0))
        visual_heading = engine.heading + steer * 0.10

        # 缩小后的冲浪板
        board_points_local = [
            (0, 76),
            (-25, 42),
            (-36, -25),
            (-19, -70),
            (0, -86),
            (19, -70),
            (36, -25),
            (25, 42),
        ]

        board_points = [
            self.local_to_screen(center, visual_heading, x, y)
            for x, y in board_points_local
        ]

        pygame.draw.polygon(self.screen, (249, 115, 22), board_points)
        pygame.draw.polygon(self.screen, (154, 52, 18), board_points, max(2, int(4 * PLAYER_DRAW_SCALE)))

        pygame.draw.line(
            self.screen,
            (254, 215, 170),
            self.local_to_screen(center, visual_heading, -21, 38),
            self.local_to_screen(center, visual_heading, 21, 38),
            max(2, int(4 * PLAYER_DRAW_SCALE))
        )

        pygame.draw.line(
            self.screen,
            (255, 237, 213),
            self.local_to_screen(center, visual_heading, 0, 64),
            self.local_to_screen(center, visual_heading, 0, -60),
            max(2, int(3 * PLAYER_DRAW_SCALE))
        )

        # 人体
        body_center = self.local_to_screen(center, visual_heading, 0, 2)
        head_center = self.local_to_screen(center, visual_heading, 0, 40)

        # 腿
        pygame.draw.line(
            self.screen,
            (30, 41, 59),
            self.local_to_screen(center, visual_heading, -8, -8),
            self.local_to_screen(center, visual_heading, -27, -36),
            max(3, int(7 * PLAYER_DRAW_SCALE))
        )

        pygame.draw.line(
            self.screen,
            (30, 41, 59),
            self.local_to_screen(center, visual_heading, 8, -8),
            self.local_to_screen(center, visual_heading, 27, -36),
            max(3, int(7 * PLAYER_DRAW_SCALE))
        )

        # 身体
        body_w = int(42 * PLAYER_DRAW_SCALE)
        body_h = int(56 * PLAYER_DRAW_SCALE)

        body_rect = pygame.Rect(0, 0, body_w, body_h)
        body_rect.center = body_center

        pygame.draw.ellipse(self.screen, (37, 99, 235), body_rect)
        pygame.draw.ellipse(self.screen, (30, 64, 175), body_rect, max(2, int(3 * PLAYER_DRAW_SCALE)))

        # 衣服高光
        pygame.draw.line(
            self.screen,
            (147, 197, 253),
            self.local_to_screen(center, visual_heading, -8, 24),
            self.local_to_screen(center, visual_heading, -8, -18),
            max(2, int(4 * PLAYER_DRAW_SCALE))
        )

        pygame.draw.line(
            self.screen,
            (147, 197, 253),
            self.local_to_screen(center, visual_heading, 8, 24),
            self.local_to_screen(center, visual_heading, 8, -18),
            max(2, int(4 * PLAYER_DRAW_SCALE))
        )

        # 手臂
        skin = (245, 178, 121)

        pygame.draw.line(
            self.screen,
            skin,
            self.local_to_screen(center, visual_heading, -20, 10),
            self.local_to_screen(center, visual_heading, -49, 27),
            max(3, int(8 * PLAYER_DRAW_SCALE))
        )

        pygame.draw.line(
            self.screen,
            skin,
            self.local_to_screen(center, visual_heading, 20, 10),
            self.local_to_screen(center, visual_heading, 49, 27),
            max(3, int(8 * PLAYER_DRAW_SCALE))
        )

        # 头
        head_r = max(8, int(20 * PLAYER_DRAW_SCALE))

        pygame.draw.circle(self.screen, skin, head_center, head_r)
        pygame.draw.circle(self.screen, (120, 53, 15), head_center, head_r, max(2, int(3 * PLAYER_DRAW_SCALE)))

        # 头发
        hair_points = [
            self.local_to_screen(center, visual_heading, -18, 53),
            self.local_to_screen(center, visual_heading, -4, 67),
            self.local_to_screen(center, visual_heading, 16, 58),
            self.local_to_screen(center, visual_heading, 11, 40),
            self.local_to_screen(center, visual_heading, -16, 40),
        ]

        pygame.draw.polygon(self.screen, (67, 20, 7), hair_points)

        # 移动方向箭头，缩小一点
        arrow_start = self.local_to_screen(center, visual_heading, 0, 92)
        arrow_end = self.local_to_screen(center, visual_heading, 0, 138)

        pygame.draw.line(self.screen, (255, 255, 255), arrow_start, arrow_end, max(2, int(4 * PLAYER_DRAW_SCALE)))

        left_arrow = self.local_to_screen(center, visual_heading, -10, 123)
        right_arrow = self.local_to_screen(center, visual_heading, 10, 123)

        pygame.draw.polygon(
            self.screen,
            (255, 255, 255),
            [arrow_end, left_arrow, right_arrow]
        )

    # ============================================================
    # 浮动文字
    # ============================================================
    def draw_float_texts(self, engine):
        for t in engine.float_texts:
            screen = self.world_to_screen(engine, t["pos"])
            pos = (screen.x, screen.y + t["offset_y"])

            draw_text(
                self.screen,
                self.font,
                t["text"],
                pos,
                t["color"],
                center=True
            )

    # ============================================================
    # HUD
    # ============================================================
    def draw_hud(self, engine, control, serial_status, serial_ok):
        panel = pygame.Rect(24, 22, 620, 132)

        pygame.draw.rect(self.screen, (255, 255, 255), panel, border_radius=18)
        pygame.draw.rect(self.screen, (186, 230, 253), panel, 3, border_radius=18)

        hearts = "❤" * engine.lives + "♡" * (3 - engine.lives)

        draw_text(
            self.screen,
            self.font_mid,
            f"金币：{engine.coin_count} / {engine.target_coins}",
            (48, 42),
            (15, 23, 42)
        )

        draw_text(
            self.screen,
            self.font,
            f"生命：{hearts}",
            (48, 84),
            (220, 38, 38)
        )

        draw_text(
            self.screen,
            self.font,
            f"速度：{int(engine.speed)}",
            (230, 84),
            (3, 105, 161)
        )

        steer = control.get("steer", 0.0)
        accel = control.get("accelerate", 0.0)

        draw_text(
            self.screen,
            self.font,
            f"转向：{steer:+.2f}  前后：{accel:+.2f}",
            (365, 84),
            (51, 65, 85)
        )

        progress = clamp(engine.coin_count / engine.target_coins, 0, 1)

        pygame.draw.rect(
            self.screen,
            (226, 232, 240),
            (48, 122, 550, 12),
            border_radius=6
        )

        pygame.draw.rect(
            self.screen,
            (34, 197, 94),
            (48, 122, int(550 * progress), 12),
            border_radius=6
        )

        status_color = (22, 163, 74) if serial_ok else (245, 158, 11)

        draw_text(
            self.screen,
            self.font_small,
            serial_status,
            (24, self.screen_h - 36),
            status_color
        )

        draw_text(
            self.screen,
            self.font_small,
            "端坐自动前进    前倾加速    后倾停止    C 校准    Space 开始/重开    Esc 退出",
            (self.screen_w - 820, self.screen_h - 36),
            (255, 255, 255)
        )

    # ============================================================
    # 热力图
    # ============================================================
    def draw_heatmap_panel(self, corrected_matrix, control, current_data):
        w, h = 370, 232
        x = self.screen_w - w - 26
        y = 24

        panel = pygame.Rect(x, y, w, h)

        pygame.draw.rect(self.screen, (255, 255, 255), panel, border_radius=18)
        pygame.draw.rect(self.screen, (203, 213, 225), panel, 2, border_radius=18)

        draw_text(
            self.screen,
            self.font,
            "实时压力热力图",
            (x + 18, y + 14),
            (15, 23, 42)
        )

        if corrected_matrix is None:
            corrected_matrix = np.zeros((16, 32), dtype=np.float32)

        corrected_matrix = np.asarray(corrected_matrix)

        if corrected_matrix.shape != (16, 32):
            corrected_matrix = np.zeros((16, 32), dtype=np.float32)

        heat_x = x + 18
        heat_y = y + 52
        heat_w = w - 36
        heat_h = 112

        rows, cols = corrected_matrix.shape
        cell_w = heat_w / cols
        cell_h = heat_h / rows

        for r in range(rows):
            for c in range(cols):
                color = value_to_rgb(corrected_matrix[r, c])
                rect = pygame.Rect(
                    int(heat_x + c * cell_w),
                    int(heat_y + r * cell_h),
                    int(math.ceil(cell_w)),
                    int(math.ceil(cell_h))
                )
                pygame.draw.rect(self.screen, color, rect)

        pygame.draw.rect(
            self.screen,
            (100, 116, 139),
            (heat_x, heat_y, heat_w, heat_h),
            2
        )

        center = control.get("center", {})

        if center.get("valid", False):
            cx = center.get("cx", 15.5)
            cy = center.get("cy", 7.5)

            px = heat_x + cx / 31.0 * heat_w
            py = heat_y + cy / 15.0 * heat_h

            pygame.draw.circle(self.screen, (17, 24, 39), (int(px), int(py)), 7)
            pygame.draw.circle(self.screen, (255, 255, 255), (int(px), int(py)), 7, 2)

        posture = "--"

        if current_data:
            posture = current_data.get("posture_name", "--")

            if not current_data.get("is_seated", False):
                posture = "离座 / 键盘调试"

        draw_text(
            self.screen,
            self.font_small,
            f"坐姿：{posture}",
            (x + 18, y + 176),
            (51, 65, 85)
        )

        if current_data:
            peak = current_data.get("peak_pressure", 0)
            mean = current_data.get("mean_pressure", 0)

            draw_text(
                self.screen,
                self.font_small,
                f"峰值：{peak}   平均：{mean:.1f}",
                (x + 18, y + 201),
                (51, 65, 85)
            )
        else:
            draw_text(
                self.screen,
                self.font_small,
                "等待串口数据，可用键盘调试",
                (x + 18, y + 201),
                (100, 116, 139)
            )

    # ============================================================
    # 闪屏
    # ============================================================
    def draw_flash(self, engine):
        if engine.hit_flash_timer <= 0:
            return

        overlay = pygame.Surface((self.screen_w, self.screen_h), pygame.SRCALPHA)
        overlay.fill((239, 68, 68, 90))
        self.screen.blit(overlay, (0, 0))

    # ============================================================
    # 状态覆盖层
    # ============================================================
    def draw_state_overlay(self, engine):
        if engine.state == "running":
            return

        overlay = pygame.Surface((self.screen_w, self.screen_h), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 145))
        self.screen.blit(overlay, (0, 0))

        if engine.state == "ready":
            title = "智能坐垫高级冲浪"
            lines = [
                "端坐自动向前进",
                "前倾加速，后倾立即停止",
                "左右倾斜控制方向",
                f"收集 {engine.target_coins} 个金币即可胜利",
                "建议端坐后按 C 校准中心",
                "按 Space 开始"
            ]
            title_color = (255, 255, 255)

        elif engine.state == "win":
            title = "挑战成功！"
            lines = [
                f"你收集了 {engine.coin_count} 个金币",
                f"移动距离：{int(engine.distance)}",
                "按 Space 重新开始"
            ]
            title_color = (187, 247, 208)

        else:
            title = "游戏失败"
            lines = [
                f"金币：{engine.coin_count} / {engine.target_coins}",
                f"移动距离：{int(engine.distance)}",
                "按 Space 重新开始"
            ]
            title_color = (254, 202, 202)

        draw_text(
            self.screen,
            self.font_big,
            title,
            (self.screen_w / 2, self.screen_h / 2 - 180),
            title_color,
            center=True
        )

        for i, line in enumerate(lines):
            is_last = i == len(lines) - 1

            draw_text(
                self.screen,
                self.font_mid if is_last else self.font,
                line,
                (self.screen_w / 2, self.screen_h / 2 - 95 + i * 42),
                (253, 230, 138) if is_last else (224, 242, 254),
                center=True
            )
