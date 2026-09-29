# heatmap_view.py
import tkinter as tk
from PIL import Image, ImageTk, ImageFilter


class PressureHeatmapView:
    """
    压力热力图绘制模块。

    不做行顺序纠正。
    左图 matrix[:, :16]
    右图 matrix[:, 16:]
    """

    def __init__(self, parent, canvas_width=500, canvas_height=500):
        self.parent = parent
        self.canvas_width = canvas_width
        self.canvas_height = canvas_height

        self.canvas_left = tk.Canvas(
            parent,
            width=canvas_width,
            height=canvas_height,
            bg="#FFFFFF",
            highlightthickness=0
        )

        self.canvas_right = tk.Canvas(
            parent,
            width=canvas_width,
            height=canvas_height,
            bg="#FFFFFF",
            highlightthickness=0
        )

        self.canvas_left_img = None
        self.canvas_right_img = None

    def grid(self):
        self.canvas_left.grid(row=0, column=0, padx=12, pady=12)
        self.canvas_right.grid(row=0, column=1, padx=12, pady=12)

    def value_to_rgb(self, val):
        points = [
            (0, (229, 231, 235)),
            (40, (229, 231, 235)),
            (120, (44, 123, 182)),
            (300, (26, 150, 65)),
            (600, (253, 174, 97)),
            (900, (215, 25, 28))
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

    def draw_part(self, canvas, data_part, side):
        canvas.delete("all")

        canvas_width = int(canvas["width"])
        canvas_height = int(canvas["height"])

        rows, cols = data_part.shape

        small_img = Image.new("RGB", (cols, rows), "#FFFFFF")
        pixels = small_img.load()

        for r in range(rows):
            for c in range(cols):
                pixels[c, r] = self.value_to_rgb(data_part[r, c])

        try:
            resample_method = Image.Resampling.BICUBIC
        except AttributeError:
            resample_method = Image.BICUBIC

        heat_img = small_img.resize(
            (canvas_width - 30, canvas_height - 30),
            resample_method
        )

        heat_img = heat_img.filter(ImageFilter.GaussianBlur(radius=5))
        heat_img = heat_img.filter(ImageFilter.SMOOTH_MORE)

        bg = Image.new("RGB", (canvas_width, canvas_height), "#FFFFFF")
        bg.paste(heat_img, (15, 15))

        tk_img = ImageTk.PhotoImage(bg)
        canvas.create_image(0, 0, anchor="nw", image=tk_img)

        if side == "left":
            self.canvas_left_img = tk_img
        else:
            self.canvas_right_img = tk_img

    def update(self, matrix):
        self.draw_part(self.canvas_left, matrix[:, :16], "left")
        self.draw_part(self.canvas_right, matrix[:, 16:], "right")