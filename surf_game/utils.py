# surf_game/utils.py
import math
import pygame


def clamp(v, lo, hi):
    return max(lo, min(hi, v))


def draw_text(surface, font, text, pos, color=(255, 255, 255), center=False):
    img = font.render(str(text), True, color)
    rect = img.get_rect()

    if center:
        rect.center = pos
    else:
        rect.topleft = pos

    surface.blit(img, rect)


def value_to_rgb(val):
    points = [
        (0, (229, 231, 235)),
        (40, (229, 231, 235)),
        (120, (44, 123, 182)),
        (300, (26, 150, 65)),
        (600, (253, 174, 97)),
        (900, (215, 25, 28)),
    ]

    val = float(val)

    if val <= points[0][0]:
        return points[0][1]

    for i in range(len(points) - 1):
        v1, c1 = points[i]
        v2, c2 = points[i + 1]

        if v1 <= val <= v2:
            t = (val - v1) / (v2 - v1) if v2 != v1 else 0
            r = int(c1[0] + (c2[0] - c1[0]) * t)
            g = int(c1[1] + (c2[1] - c1[1]) * t)
            b = int(c1[2] + (c2[2] - c1[2]) * t)
            return r, g, b

    return points[-1][1]


def local_to_screen(center, heading, lx, ly):
    forward = pygame.Vector2(math.sin(heading), -math.cos(heading))
    right = pygame.Vector2(math.cos(heading), math.sin(heading))

    p = pygame.Vector2(center) + right * lx + forward * ly
    return int(p.x), int(p.y)