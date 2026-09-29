# surf_game/game_engine.py
import math
import random

import pygame

from config import (
    TARGET_COINS,
    BASE_SPEED,
    MAX_SPEED,
    ACCEL_RATE,
    NATURAL_DRAG,
    TURN_RATE,
    BACK_STOP_THRESHOLD,
    MAX_HEADING_ANGLE,
)
from utils import clamp


class GameEngine:
    """
    游戏逻辑。

    修改点：
    1. 小人只能向前走。
    2. 方向限制在初始前方 180 度范围。
    3. 不能回头。
    """

    def __init__(self):
        self.reset()

    def reset(self):
        self.state = "ready"

        self.player_pos = pygame.Vector2(0, 0)
        self.camera_pos = pygame.Vector2(0, 0)

        self.heading = 0.0
        self.speed = BASE_SPEED

        self.distance = 0.0

        self.coin_count = 0
        self.target_coins = TARGET_COINS

        self.lives = 3
        self.invincible_timer = 0.0
        self.hit_flash_timer = 0.0

        self.coins = []
        self.obstacles = []
        self.particles = []
        self.float_texts = []

        self.generate_initial_world()

    def start(self):
        if self.state in ("ready", "win", "fail"):
            self.reset()
            self.state = "running"

    def forward_vec(self):
        return pygame.Vector2(math.sin(self.heading), -math.cos(self.heading))

    def right_vec(self):
        return pygame.Vector2(math.cos(self.heading), math.sin(self.heading))

    def generate_initial_world(self):
        for _ in range(80):
            self.spawn_coin()

        for _ in range(46):
            self.spawn_obstacle()

    def spawn_coin(self):
        forward = self.forward_vec()
        right = self.right_vec()

        dist = random.uniform(420, 3600)
        side = random.uniform(-1400, 1400)

        pos = self.player_pos + forward * dist + right * side

        self.coins.append({
            "pos": pos,
            "radius": 18,
            "phase": random.random() * 10,
        })

    def spawn_obstacle(self):
        forward = self.forward_vec()
        right = self.right_vec()

        dist = random.uniform(650, 3900)
        side = random.uniform(-1500, 1500)

        pos = self.player_pos + forward * dist + right * side

        self.obstacles.append({
            "pos": pos,
            "radius": random.randint(28, 56),
            "kind": random.choice(["rock", "buoy", "wood", "shark"]),
            "phase": random.random() * 10,
        })

    def maintain_world(self):
        while len(self.coins) < 85:
            self.spawn_coin()

        while len(self.obstacles) < 50:
            self.spawn_obstacle()

        self.coins = [
            c for c in self.coins
            if c["pos"].distance_to(self.player_pos) < 5200
        ]

        self.obstacles = [
            o for o in self.obstacles
            if o["pos"].distance_to(self.player_pos) < 5600
        ]

    def update(self, dt, control):
        if self.state != "running":
            return

        steer = float(control.get("steer", 0.0))
        accel = float(control.get("accelerate", 0.0))

        # 速度逻辑
        if accel <= BACK_STOP_THRESHOLD:
            self.speed = 0.0

        else:
            if accel > 0.08:
                self.speed += ACCEL_RATE * accel * dt

            else:
                if self.speed < BASE_SPEED:
                    self.speed += ACCEL_RATE * 0.45 * dt
                    if self.speed > BASE_SPEED:
                        self.speed = BASE_SPEED

                elif self.speed > BASE_SPEED:
                    self.speed *= NATURAL_DRAG
                    if self.speed < BASE_SPEED:
                        self.speed = BASE_SPEED

                else:
                    self.speed = BASE_SPEED

        self.speed = clamp(self.speed, 0.0, MAX_SPEED)

        # 转向逻辑：限制在前方 180 度范围内
        if self.speed > 1:
            turn_strength = 0.45 + 0.75 * (self.speed / MAX_SPEED)
            self.heading += steer * TURN_RATE * turn_strength * dt

            self.heading = clamp(
                self.heading,
                -MAX_HEADING_ANGLE,
                MAX_HEADING_ANGLE
            )

        old_pos = self.player_pos.copy()

        # 速度永远非负，只沿当前朝向前进
        self.player_pos += self.forward_vec() * self.speed * dt

        self.distance += self.player_pos.distance_to(old_pos)

        self.camera_pos += (self.player_pos - self.camera_pos) * min(1.0, 6.0 * dt)

        if self.invincible_timer > 0:
            self.invincible_timer -= dt

        if self.hit_flash_timer > 0:
            self.hit_flash_timer -= dt

        self.update_particles(dt)
        self.check_coin_collision()
        self.check_obstacle_collision()
        self.maintain_world()

        if self.coin_count >= self.target_coins:
            self.state = "win"

    def update_particles(self, dt):
        if self.speed > 230:
            back = -self.forward_vec()
            right = self.right_vec()

            amount = 1 if self.speed < 460 else 2

            for _ in range(amount):
                pos = (
                    self.player_pos
                    + back * random.uniform(34, 60)
                    + right * random.uniform(-28, 28)
                )

                vel = (
                    back * random.uniform(70, 180)
                    + right * random.uniform(-80, 80)
                )

                self.particles.append({
                    "pos": pos,
                    "vel": vel,
                    "life": random.uniform(0.35, 0.65),
                    "max_life": 0.65,
                    "radius": random.uniform(3, 7),
                })

        for p in self.particles:
            p["pos"] += p["vel"] * dt
            p["life"] -= dt

        self.particles = [p for p in self.particles if p["life"] > 0]

        for t in self.float_texts:
            t["life"] -= dt
            t["offset_y"] -= 45 * dt

        self.float_texts = [t for t in self.float_texts if t["life"] > 0]

    def add_float_text(self, text, pos, color):
        self.float_texts.append({
            "text": text,
            "pos": pos.copy(),
            "offset_y": 0,
            "life": 0.9,
            "color": color,
        })

    def check_coin_collision(self):
        remain = []

        for c in self.coins:
            if c["pos"].distance_to(self.player_pos) < 55:
                self.coin_count += 1
                self.add_float_text("+1 金币", c["pos"], (255, 236, 153))
            else:
                remain.append(c)

        self.coins = remain

    def check_obstacle_collision(self):
        if self.invincible_timer > 0:
            return

        for o in self.obstacles:
            hit_radius = o["radius"] + 28

            if o["pos"].distance_to(self.player_pos) < hit_radius:
                self.lives -= 1
                self.invincible_timer = 1.2
                self.hit_flash_timer = 0.18

                self.speed *= 0.35

                self.add_float_text("-1 生命", self.player_pos, (255, 160, 160))

                o["pos"] += self.forward_vec() * 1800

                if self.lives <= 0:
                    self.state = "fail"

                break

    def world_to_screen(self, pos, screen_w, screen_h, scale=1.0):
        center = pygame.Vector2(screen_w / 2, screen_h / 2)
        return center + (pos - self.camera_pos) * scale