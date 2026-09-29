# main_app.py

import os
import datetime
from queue import Queue, Empty

import customtkinter as ctk

from serial_backend import SmartCushionSerialReceiver
from heatmap_view import PressureHeatmapView
from posture_image_view import PostureImageView
from game_launcher import GameLauncher

# 切换为暗色模式，显得更高级、专注
ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

# 高级感暗黑配色调色板
COLOR_BG_MAIN = "#0A0A0B"  # 主背景（纯净极暗）
COLOR_BG_SIDEBAR = "#111113"  # 侧边栏
COLOR_CARD = "#1A1A1D"  # 卡片/面板背景
COLOR_BORDER = "#2C2C30"  # 细腻的边框线
COLOR_TEXT_MAIN = "#FAFAFA"  # 主文字
COLOR_TEXT_SUB = "#A1A1AA"  # 副文字 (高级灰)
COLOR_ACCENT = "#2563EB"  # 科技蓝 (主高亮色)
COLOR_ACCENT_HOVER = "#1D4ED8"  # 交互悬浮状态色
COLOR_SUCCESS = "#10B981"  # 成功/在线 (翡翠绿)
COLOR_WARNING = "#F59E0B"  # 警告/等待 (琥珀黄)
COLOR_DANGER = "#EF4444"  # 危险/停止 (玫瑰红)


class SmartCushionApp(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("智能压力坐垫上位机")

        self.geometry("1780x910")
        self.minsize(1660, 860)
        self.resizable(True, True)

        self.configure(fg_color=COLOR_BG_MAIN)

        self.base_dir = os.path.dirname(os.path.abspath(__file__))

        self.data_queue = Queue()
        self.status_queue = Queue()

        self.serial_receiver = SmartCushionSerialReceiver(
            port="COM18",
            baudrate=460800,
            data_queue=self.data_queue,
            status_queue=self.status_queue
        )

        self.game_launcher = GameLauncher(
            game_dir="surf_game",
            on_before_start=self.pause_serial_for_game,
            on_after_exit=self.resume_serial_after_game,
            port_provider=self.get_current_serial_port,
            baudrate_provider=self.get_current_baudrate
        )

        self.game_button_enable = False
        self.last_button_flag = 0

        self.current_page = "monitor"
        self.latest_data = None
        self.latest_matrix = None

        self.collecting = False
        self.current_file = None
        self.current_file_path = None
        self.saved_count = 0

        self.posture_options = {
            "端坐": 0,
            "前倾": 1,
            "后倾": 2,
            "左倾": 3,
            "右倾": 4,
            "左腿离地二郎腿": 5,
            "右腿离地二郎腿": 6
        }

        # 适配暗色模式的高级状态指示色
        self.posture_color = {
            "端坐": COLOR_SUCCESS,
            "前倾": "#2563EB",  # 靛蓝
            "后倾": "#2563EB",
            "左倾": "#F59E0B",  # 紫罗兰
            "右倾": "#F59E0B",
            "左腿离地二郎腿": COLOR_DANGER,
            "右腿离地二郎腿": COLOR_DANGER,
            "离座": COLOR_TEXT_SUB
        }

        self.create_layout()
        self.show_monitor_page()

        self.serial_receiver.start()

        self.update_loop()

        self.protocol("WM_DELETE_WINDOW", self.on_close)

    # ========================================================
    # 基础布局
    # ========================================================

    def create_layout(self):
        self.grid_columnconfigure(0, weight=0)
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        self.sidebar = ctk.CTkFrame(
            self,
            width=230,  # 稍微加宽一点使内容有呼吸感
            fg_color=COLOR_BG_SIDEBAR,
            corner_radius=0
        )
        self.sidebar.grid(row=0, column=0, sticky="ns")
        self.sidebar.grid_propagate(False)

        logo_box = ctk.CTkFrame(self.sidebar, fg_color="transparent")
        logo_box.pack(fill="x", padx=20, pady=(35, 30))

        ctk.CTkLabel(
            logo_box,
            text="Smart",
            font=("Microsoft YaHei", 32, "bold"),
            text_color=COLOR_TEXT_MAIN
        ).pack(anchor="w")

        ctk.CTkLabel(
            logo_box,
            text="Cushion",
            font=("Microsoft YaHei", 32, "bold"),
            text_color=COLOR_ACCENT
        ).pack(anchor="w", pady=(0, 2))

        ctk.CTkLabel(
            logo_box,
            text="AI 坐姿监测终端",
            font=("Microsoft YaHei", 22),
            text_color=COLOR_TEXT_SUB
        ).pack(anchor="w", pady=(4, 0))

        self.btn_monitor = self.create_side_btn("坐姿实时提醒", self.show_monitor_page, True)
        self.btn_collect = self.create_side_btn("训练集采集", self.show_collect_page, False)
        self.btn_open_game = self.create_side_btn("放松小游戏", self.open_game_from_ui, False)

        # 侧边栏下方的间距
        ctk.CTkFrame(self.sidebar, fg_color="transparent", height=20).pack(expand=True)

        game_panel = ctk.CTkFrame(self.sidebar, fg_color=COLOR_CARD, corner_radius=12, border_width=1,
                                  border_color=COLOR_BORDER)
        game_panel.pack(fill="x", padx=16, pady=(10, 10))

        ctk.CTkLabel(
            game_panel,
            text="传感器按钮启动游戏",
            font=("Microsoft YaHei", 13, "bold"),
            text_color=COLOR_TEXT_MAIN
        ).pack(anchor="w", padx=16, pady=(16, 8))

        self.btn_game_button_enable = ctk.CTkButton(
            game_panel,
            text="功能关闭",
            width=100,
            height=34,
            corner_radius=8,
            fg_color="#27272A",
            hover_color="#3F3F46",
            font=("Microsoft YaHei", 12, "bold"),
            text_color=COLOR_TEXT_SUB,
            command=self.toggle_game_button_enable
        )
        self.btn_game_button_enable.pack(anchor="w", padx=16, pady=(0, 16))

        self.create_serial_panel()

        self.content = ctk.CTkFrame(
            self,
            fg_color=COLOR_BG_MAIN,
            corner_radius=0
        )
        self.content.grid(row=0, column=1, sticky="nsew")
        self.content.grid_columnconfigure(0, weight=1)
        self.content.grid_rowconfigure(1, weight=1)

    def create_side_btn(self, text, command, is_active):
        button = ctk.CTkButton(
            self.sidebar,
            text=text,
            height=48,
            corner_radius=10,
            fg_color=(COLOR_ACCENT if is_active else "transparent"),
            hover_color=(COLOR_ACCENT_HOVER if is_active else COLOR_CARD),
            text_color=(COLOR_TEXT_MAIN if is_active else COLOR_TEXT_SUB),
            font=("Microsoft YaHei", 15, "bold"),
            anchor="w",
            command=command
        )
        button.pack(fill="x", padx=16, pady=4)
        return button

    def create_serial_panel(self):
        panel = ctk.CTkFrame(self.sidebar, fg_color=COLOR_CARD, corner_radius=12, border_width=1,
                             border_color=COLOR_BORDER)
        panel.pack(side="bottom", fill="x", padx=16, pady=20)

        ctk.CTkLabel(
            panel,
            text="串口配置",
            font=("Microsoft YaHei", 14, "bold"),
            text_color=COLOR_TEXT_MAIN
        ).pack(anchor="w", padx=16, pady=(16, 8))

        # Port
        self.port_entry = ctk.CTkEntry(
            panel,
            height=34,
            font=("Microsoft YaHei", 12),
            fg_color=COLOR_BG_MAIN,
            text_color=COLOR_TEXT_MAIN,
            border_width=1,
            border_color=COLOR_BORDER,
            corner_radius=8
        )
        self.port_entry.pack(fill="x", padx=16, pady=(4, 8))
        self.port_entry.insert(0, "COM18")

        # Baudrate
        self.baud_entry = ctk.CTkEntry(
            panel,
            height=34,
            font=("Microsoft YaHei", 12),
            fg_color=COLOR_BG_MAIN,
            text_color=COLOR_TEXT_MAIN,
            border_width=1,
            border_color=COLOR_BORDER,
            corner_radius=8
        )
        self.baud_entry.pack(fill="x", padx=16, pady=(4, 12))
        self.baud_entry.insert(0, "460800")

        self.reconnect_btn = ctk.CTkButton(
            panel,
            text="重新连接",
            height=36,
            corner_radius=8,
            font=("Microsoft YaHei", 13, "bold"),
            fg_color=COLOR_ACCENT,
            hover_color=COLOR_ACCENT_HOVER,
            command=self.restart_serial
        )
        self.reconnect_btn.pack(fill="x", padx=16, pady=(0, 12))

        self.serial_status_label = ctk.CTkLabel(
            panel,
            text="● 等待连接",
            font=("Microsoft YaHei", 12, "bold"),
            text_color=COLOR_WARNING,
            wraplength=175,
            justify="left"
        )
        self.serial_status_label.pack(anchor="w", padx=16, pady=(0, 16))

    def create_topbar(self, title, subtitle):
        topbar = ctk.CTkFrame(self.content, height=80, fg_color="transparent", corner_radius=0)
        topbar.grid(row=0, column=0, sticky="ew", padx=24, pady=(20, 0))
        topbar.grid_propagate(False)
        topbar.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            topbar,
            text=title,
            font=("Microsoft YaHei", 28, "bold"),
            text_color=COLOR_TEXT_MAIN
        ).grid(row=0, column=0, sticky="w")

        ctk.CTkLabel(
            topbar,
            text=subtitle,
            font=("Microsoft YaHei", 13),
            text_color=COLOR_TEXT_SUB
        ).grid(row=1, column=0, sticky="w", pady=(2, 0))

        self.time_label = ctk.CTkLabel(
            topbar,
            text="",
            font=("Microsoft YaHei", 13),
            text_color=COLOR_TEXT_SUB
        )
        self.time_label.grid(row=0, column=1, sticky="e")

    def clear_content(self):
        for widget in self.content.winfo_children():
            widget.destroy()

    # ========================================================
    # 串口控制
    # ========================================================

    def get_current_serial_port(self):
        try:
            port = self.port_entry.get().strip()
            if port: return port
        except Exception:
            pass
        return "COM18"

    def get_current_baudrate(self):
        try:
            return int(self.baud_entry.get().strip())
        except Exception:
            return 460800

    def restart_serial(self):
        port = self.get_current_serial_port()
        baudrate = self.get_current_baudrate()
        self.baud_entry.delete(0, "end")
        self.baud_entry.insert(0, str(baudrate))
        self.serial_receiver.update_port(port, baudrate)
        self.serial_status_label.configure(text="● 正在重新连接...", text_color=COLOR_WARNING)

    # ========================================================
    # 游戏控制
    # ========================================================

    def set_serial_status(self, text, color):
        try:
            self.after(0, lambda: self._apply_serial_status(text, color))
        except Exception:
            pass

    def _apply_serial_status(self, text, color):
        try:
            if self.serial_status_label.winfo_exists():
                self.serial_status_label.configure(text=text, text_color=color)
        except Exception:
            pass

    def pause_serial_for_game(self):
        try:
            self.serial_receiver.stop()
        except Exception as error:
            print(f"[UI] 暂停串口失败：{error}")
        self.set_serial_status("● 游戏运行中 (串口暂停)", COLOR_WARNING)

    def resume_serial_after_game(self):
        try:
            self.serial_receiver.start()
            self.set_serial_status("● 正在恢复串口...", COLOR_WARNING)
        except Exception as error:
            print(f"[UI] 恢复串口失败：{error}")

    def open_game_from_ui(self):
        if self.game_launcher.is_running():
            self.serial_status_label.configure(text="● 游戏已经在运行", text_color=COLOR_WARNING)
            return
        self.game_launcher.launch()

    def toggle_game_button_enable(self):
        self.game_button_enable = not self.game_button_enable
        if self.game_button_enable:
            self.btn_game_button_enable.configure(
                text="功能开启",
                fg_color=COLOR_SUCCESS,
                text_color=COLOR_TEXT_MAIN
            )
        else:
            self.btn_game_button_enable.configure(
                text="功能关闭",
                fg_color="#27272A",
                text_color=COLOR_TEXT_SUB
            )

    def check_mcu_button_open_game(self, data):
        if data is None: return
        try:
            button_flag = int(data.get("button_flag", 0))
        except Exception:
            button_flag = 0

        rising_edge = (self.last_button_flag == 0 and button_flag == 1)

        if self.game_button_enable and rising_edge and not self.game_launcher.is_running():
            self.open_game_from_ui()

        self.last_button_flag = button_flag

    # ========================================================
    # 实时监测页面
    # ========================================================

    def show_monitor_page(self):
        self.clear_content()
        self.current_page = "monitor"

        self.btn_monitor.configure(fg_color=COLOR_ACCENT, text_color=COLOR_TEXT_MAIN)
        self.btn_collect.configure(fg_color="transparent", text_color=COLOR_TEXT_SUB)

        self.create_topbar("坐姿实时监测核心", "Dashboard / Live Monitoring System")

        main = ctk.CTkFrame(self.content, fg_color="transparent")
        main.grid(row=1, column=0, sticky="nsew", padx=24, pady=(5, 20))
        main.grid_columnconfigure(0, weight=1)
        main.grid_columnconfigure(1, weight=0)
        main.grid_rowconfigure(1, weight=1)

        # ----------------------------------------------------
        # 顶部卡片区域
        # ----------------------------------------------------
        cards = ctk.CTkFrame(main, fg_color="transparent")
        cards.grid(row=0, column=0, columnspan=2, sticky="ew", pady=(0, 16))
        cards.grid_columnconfigure((0, 1, 2, 3, 4), weight=1)

        self.card_seat = self.create_card(cards, "在座状态", "--", COLOR_TEXT_SUB, "Status", 0)
        self.card_posture = self.create_card(cards, "AI 模型识别坐姿", "--", COLOR_ACCENT, "Prediction", 1)
        self.card_button = self.create_card(cards, "按键反馈", "0", COLOR_TEXT_SUB, "Button", 2)
        self.card_peak = self.create_card(cards, "峰值压力", "--", COLOR_TEXT_MAIN, "PMax", 3)
        self.card_std = self.create_card(cards, "压力标准差", "--", COLOR_TEXT_MAIN, "StdDev", 4)

        # 突出识别卡片
        self.card_posture.configure(border_color=COLOR_ACCENT, border_width=1, fg_color="#181822")

        # ----------------------------------------------------
        # 左侧 - 热力图视图
        # ----------------------------------------------------
        heat_frame = ctk.CTkFrame(
            main, fg_color=COLOR_CARD, corner_radius=16, width=1045, height=675,
            border_width=1, border_color=COLOR_BORDER
        )
        heat_frame.grid(row=1, column=0, sticky="nsew", padx=(0, 16))
        heat_frame.grid_propagate(False)

        heat_header = ctk.CTkFrame(heat_frame, fg_color="transparent")
        heat_header.pack(fill="x", padx=24, pady=(20, 10))
        heat_header.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            heat_header,
            text="物理反馈热力矩阵",
            font=("Microsoft YaHei", 20, "bold"),
            text_color=COLOR_TEXT_MAIN
        ).grid(row=0, column=0, sticky="w")

        self.heat_status_badge = ctk.CTkLabel(
            heat_header, text="LIVE", width=60, height=24,
            font=("Helvetica", 12, "bold"),
            text_color=COLOR_SUCCESS, fg_color="#064E3B", corner_radius=6
        )
        self.heat_status_badge.grid(row=0, column=1, sticky="e")

        # 热力图展示框
        canvas_outer = ctk.CTkFrame(heat_frame, fg_color=COLOR_BG_MAIN, corner_radius=12, border_width=1,
                                    border_color=COLOR_BORDER)
        canvas_outer.pack(expand=True, fill="both", padx=24, pady=(0, 24))

        canvas_box = ctk.CTkFrame(canvas_outer, fg_color="transparent", corner_radius=0)
        canvas_box.pack(expand=True)

        # 尺寸无更改
        self.monitor_heatmap = PressureHeatmapView(
            canvas_box,
            canvas_width=515,
            canvas_height=515
        )
        self.monitor_heatmap.grid()

        # ----------------------------------------------------
        # 右侧 - 系统姿势比对 (图片视觉)
        # ----------------------------------------------------
        posture_frame = ctk.CTkFrame(
            main, fg_color=COLOR_CARD, corner_radius=16, width=500, height=675,
            border_width=1, border_color=COLOR_BORDER
        )
        posture_frame.grid(row=1, column=1, sticky="nsew")
        posture_frame.grid_propagate(False)

        ctk.CTkLabel(
            posture_frame, text="当前姿势", font=("Microsoft YaHei", 16, "bold"), text_color=COLOR_TEXT_MAIN
        ).pack(anchor="w", padx=24, pady=(20, 4))

        self.posture_name_top = ctk.CTkLabel(
            posture_frame, text="等待连接", font=("Microsoft YaHei", 32, "bold"), text_color=COLOR_WARNING
        )
        self.posture_name_top.pack(anchor="w", padx=24, pady=(0, 16))

        # 容器层背景设为比页面深一点的颜色托出图片
        image_shell = ctk.CTkFrame(
            posture_frame, fg_color=COLOR_BG_MAIN, corner_radius=12, width=492, height=554,
            border_width=1, border_color=COLOR_BORDER
        )
        image_shell.pack(padx=20, pady=(0, 12))
        image_shell.pack_propagate(False)

        # 注：若你的本地姿势图片底色是纯白色导致黑色主题违和，可将这里的 background 改回 "#FFFFFF"
        # 尺寸无更改
        self.posture_image_view = PostureImageView(
            image_shell,
            image_dir=self.base_dir,
            image_width=472,
            image_height=534,
            background=COLOR_BG_MAIN
        )
        self.posture_image_view.pack(expand=True)

        if self.latest_data is not None:
            self.update_monitor_page(self.latest_data)

    def create_card(self, parent, title, value, color, description, column):
        card = ctk.CTkFrame(
            parent, fg_color=COLOR_CARD, corner_radius=12, height=90,
            border_width=1, border_color=COLOR_BORDER
        )
        card.grid(row=0, column=column, sticky="ew",
                  padx=6 if column != 0 and column != 4 else (0 if column == 0 else 6))
        card.grid_propagate(False)

        ctk.CTkLabel(card, text=title, font=("Microsoft YaHei", 12), text_color=COLOR_TEXT_SUB).pack(anchor="w",
                                                                                                     padx=16,
                                                                                                     pady=(12, 0))

        value_label = ctk.CTkLabel(card, text=value, font=("Arial", 26, "bold"), text_color=color)
        value_label.pack(anchor="w", padx=16, pady=(0, 0))

        card.v_lbl = value_label
        return card

    def update_monitor_page(self, data):
        if not hasattr(self, "monitor_heatmap"): return

        try:
            matrix = data["matrix"]
            pred = data.get("pred")
            posture_name = data.get("posture_name", "--")
            button_flag = data.get("button_flag", 0)
            peak_pressure = data.get("peak_pressure", 0)
            std_pressure = data.get("std_pressure", 0.0)
            is_seated = data.get("is_seated", False)
        except Exception:
            return

        self.monitor_heatmap.update(matrix)

        if is_seated:
            seat_text = "已入座"
            seat_color = COLOR_SUCCESS
        else:
            seat_text = "已离座"
            seat_color = COLOR_TEXT_SUB

        post_color = self.posture_color.get(posture_name, COLOR_TEXT_MAIN)

        self.card_seat.v_lbl.configure(text=seat_text, text_color=seat_color)
        self.card_posture.v_lbl.configure(text=posture_name, text_color=post_color)
        self.card_button.v_lbl.configure(text=str(button_flag))
        self.card_peak.v_lbl.configure(text=str(peak_pressure))
        self.card_std.v_lbl.configure(text=f"{std_pressure:.1f}")

        if pred is None:
            top_text = "识别数据流加载中"
            indicator_color = COLOR_WARNING
        elif int(pred) == 7:
            top_text = "当前无人就坐"
            indicator_color = COLOR_TEXT_SUB
        elif 0 <= int(pred) <= 6:
            top_text = posture_name
            indicator_color = post_color
        else:
            top_text = posture_name
            indicator_color = COLOR_TEXT_SUB

        self.posture_name_top.configure(text=top_text, text_color=indicator_color)
        self.posture_image_view.show_posture(pred, posture_name)

        try:
            self.posture_image_view.master.configure(border_color=indicator_color)
        except:
            pass

    # ========================================================
    # 训练集采集页面
    # ========================================================

    def show_collect_page(self):
        self.clear_content()
        self.current_page = "collect"

        self.btn_monitor.configure(fg_color="transparent", text_color=COLOR_TEXT_SUB)
        self.btn_collect.configure(fg_color=COLOR_ACCENT, text_color=COLOR_TEXT_MAIN)

        self.create_topbar("数据集采集中心", "Dataset Collection Engine")

        main = ctk.CTkFrame(self.content, fg_color="transparent")
        main.grid(row=1, column=0, sticky="nsew", padx=24, pady=(5, 20))
        main.grid_columnconfigure(0, weight=1)
        main.grid_columnconfigure(1, weight=0)
        main.grid_rowconfigure(0, weight=1)

        heat_frame = ctk.CTkFrame(
            main, fg_color=COLOR_CARD, corner_radius=16, width=1045, height=700,
            border_width=1, border_color=COLOR_BORDER
        )
        heat_frame.grid(row=0, column=0, sticky="nsew", padx=(0, 16))
        heat_frame.grid_propagate(False)

        ctk.CTkLabel(
            heat_frame, text="热力数据捕捉", font=("Microsoft YaHei", 20, "bold"), text_color=COLOR_TEXT_MAIN
        ).pack(anchor="w", padx=24, pady=(20, 2))
        ctk.CTkLabel(
            heat_frame, text="矩阵数据: 16x32 Point Data", font=("Arial", 12), text_color=COLOR_TEXT_SUB
        ).pack(anchor="w", padx=24, pady=(0, 16))

        canvas_outer = ctk.CTkFrame(heat_frame, fg_color=COLOR_BG_MAIN, corner_radius=12, border_width=1,
                                    border_color=COLOR_BORDER)
        canvas_outer.pack(expand=True, fill="both", padx=24, pady=(0, 24))

        canvas_box = ctk.CTkFrame(canvas_outer, fg_color="transparent", corner_radius=0)
        canvas_box.pack(expand=True)

        self.collect_heatmap = PressureHeatmapView(canvas_box, canvas_width=515, canvas_height=515)
        self.collect_heatmap.grid()

        control = ctk.CTkFrame(
            main, fg_color=COLOR_CARD, corner_radius=16, width=500, height=700,
            border_width=1, border_color=COLOR_BORDER
        )
        control.grid(row=0, column=1, sticky="nsew")
        control.grid_propagate(False)

        ctk.CTkLabel(
            control, text="采集指令", font=("Microsoft YaHei", 20, "bold"), text_color=COLOR_TEXT_MAIN
        ).pack(anchor="w", padx=24, pady=(20, 16))

        ctk.CTkLabel(
            control, text="录入标签选择", font=("Microsoft YaHei", 12), text_color=COLOR_TEXT_SUB
        ).pack(anchor="w", padx=24, pady=(0, 6))

        self.posture_var = ctk.StringVar(value="端坐")
        self.posture_menu = ctk.CTkOptionMenu(
            control,
            values=list(self.posture_options.keys()),
            variable=self.posture_var,
            height=46,
            corner_radius=8,
            fg_color=COLOR_BG_MAIN,
            button_color=COLOR_BORDER,
            button_hover_color="#3F3F46",
            dropdown_fg_color=COLOR_CARD,
            dropdown_hover_color=COLOR_BORDER,
            text_color=COLOR_TEXT_MAIN,
            font=("Microsoft YaHei", 14),
            dropdown_font=("Microsoft YaHei", 13)
        )
        self.posture_menu.pack(fill="x", padx=24)

        self.start_btn = ctk.CTkButton(
            control, text="开始流采集", height=48, corner_radius=8,
            fg_color=COLOR_ACCENT, hover_color=COLOR_ACCENT_HOVER,
            text_color=COLOR_TEXT_MAIN, font=("Microsoft YaHei", 15, "bold"),
            command=self.start_collect
        )
        self.start_btn.pack(fill="x", padx=24, pady=(24, 12))

        self.stop_btn = ctk.CTkButton(
            control, text="结束并保存", height=48, corner_radius=8,
            fg_color=COLOR_DANGER, hover_color="#BE123C",
            text_color=COLOR_TEXT_MAIN, font=("Microsoft YaHei", 15, "bold"),
            command=self.stop_collect, state="disabled"
        )
        self.stop_btn.pack(fill="x", padx=24, pady=(0, 20))

        status_box = ctk.CTkFrame(control, fg_color=COLOR_BG_MAIN, corner_radius=8, border_width=1,
                                  border_color=COLOR_BORDER)
        status_box.pack(fill="x", padx=24, pady=(0, 20))

        self.collect_status_label = ctk.CTkLabel(
            status_box, text="WAITING - 系统待机", font=("Microsoft YaHei", 12, "bold"),
            text_color=COLOR_TEXT_SUB, wraplength=400, justify="left"
        )
        self.collect_status_label.pack(anchor="w", padx=16, pady=(16, 4))

        self.count_label = ctk.CTkLabel(status_box, text="Captured: 0 frames", font=("Arial", 12),
                                        text_color=COLOR_TEXT_MAIN)
        self.count_label.pack(anchor="w", padx=16, pady=(0, 4))

        self.file_label = ctk.CTkLabel(status_box, text="Path: Null", font=("Arial", 11), text_color=COLOR_TEXT_SUB,
                                       wraplength=400, justify="left")
        self.file_label.pack(anchor="w", padx=16, pady=(0, 16))

        self.collect_info_box = ctk.CTkTextbox(
            control, height=180, corner_radius=8, fg_color=COLOR_BG_MAIN,
            text_color=COLOR_TEXT_SUB, font=("Microsoft YaHei", 12),
            border_width=1, border_color=COLOR_BORDER
        )
        self.collect_info_box.pack(fill="x", padx=24, pady=(0, 24))
        self.collect_info_box.insert(
            "1.0",
            "系统指引：\n"
            "• 通信包结构包含 16x32 Matrix 及 Boolean 标志位。\n"
            "• 本地持久化仅储存原始阵列及设定标签值。\n"
            "• 矩阵降维逻辑需在外部训练脚本中执行。\n\n"
            "操作：选定标签 -> 开始采集 -> (动作维持) -> 结束"
        )
        self.collect_info_box.configure(state="disabled")

        if self.latest_matrix is not None:
            self.collect_heatmap.update(self.latest_matrix)

    def start_collect(self):
        selected = self.posture_var.get()
        posture_code = self.posture_options[selected]
        dataset_dir = os.path.join(self.base_dir, "dataset")
        os.makedirs(dataset_dir, exist_ok=True)

        safe_name = selected.replace("/", "_").replace("\\", "_")
        filename = f"{posture_code}_{safe_name}.txt"
        file_path = os.path.join(dataset_dir, filename)

        try:
            self.current_file = open(file_path, "a", encoding="utf-8")
        except Exception as error:
            self.collect_status_label.configure(text=f"ERROR - I/O Error: {error}", text_color=COLOR_DANGER)
            return

        self.current_file_path = file_path
        self.saved_count = 0
        self.collecting = True

        self.posture_menu.configure(state="disabled")
        self.start_btn.configure(state="disabled", fg_color="#1E3A8A")
        self.stop_btn.configure(state="normal")

        self.collect_status_label.configure(text=f"RECORDING - 正在捕获 [{selected}]", text_color=COLOR_SUCCESS)
        self.count_label.configure(text="Captured: 0 frames")
        self.file_label.configure(text=f"Path: {file_path}")

    def stop_collect(self):
        self.collecting = False
        if self.current_file:
            try:
                self.current_file.flush()
                self.current_file.close()
            except:
                pass
        self.current_file = None

        for w_name, s in (("posture_menu", "normal"), ("start_btn", "normal"), ("stop_btn", "disabled")):
            if (w := getattr(self, w_name, None)) and w.winfo_exists():
                w.configure(state=s)
                if w_name == "start_btn": w.configure(fg_color=COLOR_ACCENT)

        if (lbl := getattr(self, "collect_status_label", None)) and lbl.winfo_exists():
            lbl.configure(text="WAITING - 捕获已停止", text_color=COLOR_TEXT_SUB)

    def save_one_frame(self, matrix):
        if not self.collecting or not self.current_file: return
        code = self.posture_options[self.posture_var.get()]
        line = " ".join(map(str, matrix.reshape(-1).astype(int).tolist() + [code]))

        try:
            self.current_file.write(line + "\n")
            self.current_file.flush()
            self.saved_count += 1
            self.count_label.configure(text=f"Captured: {self.saved_count} frames")
        except Exception as e:
            self.collect_status_label.configure(text=f"ERROR - 写入中断: {e}", text_color=COLOR_DANGER)
            self.stop_collect()

    def update_collect_page(self, data):
        if hasattr(self, "collect_heatmap"):
            self.collect_heatmap.update(data["matrix"])
        if self.collecting:
            self.save_one_frame(data["matrix"])

    # ========================================================
    # 主循环
    # ========================================================

    def update_loop(self):
        try:
            if self.time_label.winfo_exists():
                self.time_label.configure(text=datetime.datetime.now().strftime("%Y-%m-%d  %H:%M:%S"))
        except:
            pass

        latest_status = None
        try:
            while True: latest_status = self.status_queue.get_nowait()
        except Empty:
            pass

        if latest_status is not None:
            try:
                if latest_status.get("ok"):
                    self.serial_status_label.configure(text=latest_status.get("text", "● 设备在线"),
                                                       text_color=COLOR_SUCCESS)
                else:
                    self.serial_status_label.configure(text=latest_status.get("text", "● 等待连接"),
                                                       text_color=COLOR_WARNING)
            except:
                pass

        latest_data = None
        try:
            while True: latest_data = self.data_queue.get_nowait()
        except Empty:
            pass

        if latest_data is not None:
            self.latest_data = latest_data
            self.latest_matrix = latest_data["matrix"]
            self.check_mcu_button_open_game(latest_data)

            if self.current_page == "monitor":
                try:
                    self.update_monitor_page(latest_data)
                except Exception as e:
                    print(f"[UI] UI渲染掉帧: {e}")
            elif self.current_page == "collect":
                try:
                    self.update_collect_page(latest_data)
                except Exception as e:
                    print(f"[UI] 捕获渲染掉帧: {e}")

        self.after(50, self.update_loop)

    def on_close(self):
        if self.collecting: self.stop_collect()
        if self.serial_receiver: self.serial_receiver.stop()
        self.destroy()


if __name__ == "__main__":
    app = SmartCushionApp()
    app.mainloop()
