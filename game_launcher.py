# game_launcher.py
import os
import sys
import time
import subprocess
import threading


class GameLauncher:
    """
    从 UI 启动 Pygame 游戏。

    功能：
    1. 不阻塞 UI。
    2. 防止重复打开游戏。
    3. 游戏启动前暂停 UI 串口。
    4. 游戏退出后恢复 UI 串口。
    5. 把 UI 当前串口号和波特率传给游戏。
    """

    def __init__(
        self,
        game_dir="surf_game",
        on_before_start=None,
        on_after_exit=None,
        port_provider=None,
        baudrate_provider=None
    ):
        self.base_dir = os.path.dirname(os.path.abspath(__file__))
        self.game_dir = os.path.join(self.base_dir, game_dir)
        self.game_main = os.path.join(self.game_dir, "main.py")

        self.on_before_start = on_before_start
        self.on_after_exit = on_after_exit

        self.port_provider = port_provider
        self.baudrate_provider = baudrate_provider

        self.process = None
        self.lock = threading.Lock()

    def is_running(self):
        with self.lock:
            if self.process is None:
                return False

            return self.process.poll() is None

    def launch(self):
        with self.lock:
            if self.process is not None and self.process.poll() is None:
                return False

        t = threading.Thread(target=self._launch_thread, daemon=True)
        t.start()
        return True

    def _launch_thread(self):
        try:
            # 1. 先停止 UI 串口
            if self.on_before_start:
                self.on_before_start()

            # 2. 给 Windows 一点时间释放串口
            time.sleep(0.8)

            if not os.path.exists(self.game_main):
                print(f"[GameLauncher] 找不到游戏入口文件：{self.game_main}")
                return

            # 3. 获取 UI 当前串口参数
            port = "COM18"
            baudrate = "460800"

            if self.port_provider:
                try:
                    port = str(self.port_provider()).strip()
                except Exception:
                    port = "COM18"

            if self.baudrate_provider:
                try:
                    baudrate = str(self.baudrate_provider()).strip()
                except Exception:
                    baudrate = "460800"

            if not port:
                port = "COM18"

            if not baudrate:
                baudrate = "460800"

            # 4. 通过环境变量传给游戏
            env = os.environ.copy()
            env["SMART_CUSHION_PORT"] = port
            env["SMART_CUSHION_BAUDRATE"] = baudrate

            print(f"[GameLauncher] 启动游戏，串口={port}, 波特率={baudrate}")

            with self.lock:
                self.process = subprocess.Popen(
                    [sys.executable, self.game_main],
                    cwd=self.game_dir,
                    env=env
                )

            self.process.wait()

        except Exception as e:
            print(f"[GameLauncher] 游戏启动失败：{e}")

        finally:
            with self.lock:
                self.process = None

            # 5. 游戏退出后恢复 UI 串口
            if self.on_after_exit:
                self.on_after_exit()