# posture_image_view.py

import os
import tkinter as tk

from PIL import Image, ImageTk, ImageOps


class PostureImageView:
    """
    姿势图片显示模块。

    图片与 main_app.py 放在同一目录，映射关系为：

        姿势代码 0 -> 1.jpg -> 端坐
        姿势代码 1 -> 2.jpg -> 前倾
        姿势代码 2 -> 3.jpg -> 后倾
        姿势代码 3 -> 4.jpg -> 左倾
        姿势代码 4 -> 5.jpg -> 右倾
        姿势代码 5 -> 6.jpg -> 左腿离地二郎腿
        姿势代码 6 -> 7.jpg -> 右腿离地二郎腿

    姿势代码 7 表示离座，没有对应图片。
    """

    POSTURE_IMAGE_MAP = {
        0: "1.jpg",
        1: "2.jpg",
        2: "3.jpg",
        3: "4.jpg",
        4: "5.jpg",
        5: "6.jpg",
        6: "7.jpg"
    }

    def __init__(
        self,
        parent,
        image_dir=None,
        image_width=472,
        image_height=534,
        background="#FFFFFF"
    ):
        self.parent = parent
        self.image_width = image_width
        self.image_height = image_height
        self.background = background

        if image_dir is None:
            image_dir = os.path.dirname(os.path.abspath(__file__))

        self.image_dir = image_dir

        self.current_code = None
        self.current_image_path = None
        self.photo_image = None

        self.frame = tk.Frame(
            parent,
            width=self.image_width,
            height=self.image_height,
            bg=self.background,
            bd=0,
            highlightthickness=0
        )
        self.frame.pack_propagate(False)
        self.frame.grid_propagate(False)

        self.image_label = tk.Label(
            self.frame,
            text="等待姿势数据",
            image=None,
            compound="center",
            font=("Microsoft YaHei", 24, "bold"),
            fg="#6B7280",
            bg=self.background,
            anchor="center",
            justify="center",
            bd=0,
            highlightthickness=0
        )
        self.image_label.pack(fill="both", expand=True)

    def pack(self, **kwargs):
        self.frame.pack(**kwargs)

    def grid(self, **kwargs):
        self.frame.grid(**kwargs)

    def place(self, **kwargs):
        self.frame.place(**kwargs)

    def destroy(self):
        self.photo_image = None
        self.frame.destroy()

    def _show_text(self, text, color="#6B7280", font_size=24):
        """
        清除旧图片并显示提示文字。
        """
        self.photo_image = None
        self.current_image_path = None

        self.image_label.configure(
            image="",
            text=text,
            fg=color,
            bg=self.background,
            font=("Microsoft YaHei", font_size, "bold")
        )

    def _get_image_path(self, posture_code):
        """
        根据姿势代码获得图片路径。
        注意：代码 0 对应 1.jpg，而不是 0.jpg。
        """
        filename = self.POSTURE_IMAGE_MAP.get(posture_code)

        if filename is None:
            return None

        return os.path.join(self.image_dir, filename)

    def show_posture(self, posture_code, posture_name=""):
        """
        显示对应姿势图片。

        posture_code:
            0～6：显示 1.jpg～7.jpg
            7：显示离座提示
            None：显示等待数据
        """
        try:
            if posture_code is not None:
                posture_code = int(posture_code)
        except (TypeError, ValueError):
            posture_code = None

        # 当前代码未变化且图片已经正常显示时，不重复读取硬盘。
        if (
            posture_code == self.current_code
            and self.photo_image is not None
        ):
            return

        self.current_code = posture_code

        if posture_code is None:
            self._show_text(
                "等待姿势数据",
                color="#6B7280",
                font_size=24
            )
            return

        if posture_code == 7:
            self._show_text(
                "当前无人就坐\n\n姿势代码：7（离座）",
                color="#6B7280",
                font_size=25
            )
            return

        image_path = self._get_image_path(posture_code)

        if image_path is None:
            self._show_text(
                f"未知姿势代码：{posture_code}",
                color="#DC2626",
                font_size=22
            )
            return

        if not os.path.isfile(image_path):
            filename = os.path.basename(image_path)

            self._show_text(
                f"当前姿势：{posture_name}\n\n"
                f"找不到姿势图片\n{filename}\n\n"
                f"请将图片放在程序目录中",
                color="#DC2626",
                font_size=20
            )
            return

        try:
            with Image.open(image_path) as source_image:
                image = source_image.convert("RGB")

            try:
                resample_method = Image.Resampling.LANCZOS
            except AttributeError:
                resample_method = Image.LANCZOS

            # 保持原图比例，将图片完整放入 472×534 区域。
            # 不会拉伸图片，也不会裁剪图片。
            display_image = ImageOps.contain(
                image,
                (self.image_width, self.image_height),
                method=resample_method
            )

            background_image = Image.new(
                "RGB",
                (self.image_width, self.image_height),
                self.background
            )

            paste_x = (
                self.image_width - display_image.width
            ) // 2

            paste_y = (
                self.image_height - display_image.height
            ) // 2

            background_image.paste(
                display_image,
                (paste_x, paste_y)
            )

            self.photo_image = ImageTk.PhotoImage(background_image)
            self.current_image_path = image_path

            self.image_label.configure(
                image=self.photo_image,
                text="",
                bg=self.background
            )

        except Exception as error:
            self._show_text(
                f"姿势图片加载失败\n\n{error}",
                color="#DC2626",
                font_size=18
            )

    def clear(self):
        """
        清除当前图片，恢复等待状态。
        """
        self.current_code = None
        self.current_image_path = None

        self._show_text(
            "等待姿势数据",
            color="#6B7280",
            font_size=24
        )
