# surf_game/serial_backend.py
import time
import threading
from queue import Queue

import numpy as np

try:
    import serial
except Exception:
    serial = None

from config import POSTURE_MAP, SEATED_PEAK_THRESHOLD


class SerialReceiver:
    """
    游戏串口接收模块。

    支持：
    514：512 压力值 + pred + button_flag
    513：512 压力值 + pred
    512：只有压力矩阵
    """

    def __init__(
        self,
        port="COM18",
        baudrate=460800,
        data_queue=None,
        status_queue=None,
        reconnect_interval=1.0
    ):
        self.port = port
        self.baudrate = baudrate
        self.data_queue = data_queue if data_queue is not None else Queue()
        self.status_queue = status_queue if status_queue is not None else Queue()
        self.reconnect_interval = reconnect_interval

        self.ser = None
        self.running = False
        self.thread = None

    def start(self):
        if self.running:
            return

        self.running = True
        self.thread = threading.Thread(target=self._main_loop, daemon=True)
        self.thread.start()

    def stop(self):
        self.running = False

        try:
            if self.ser and self.ser.is_open:
                self.ser.close()
        except Exception:
            pass

        if self.thread and self.thread.is_alive():
            self.thread.join(timeout=1)

    def _put_status(self, text, ok=False):
        try:
            self.status_queue.put({
                "text": text,
                "ok": ok
            })
        except Exception:
            pass

    def _open_serial(self):
        if serial is None:
            self._put_status("● 未安装 pyserial，可用键盘调试", False)
            return False

        try:
            self.ser = serial.Serial(
                port=self.port,
                baudrate=self.baudrate,
                timeout=0.2
            )

            self._put_status(f"● 串口已连接：{self.port}", True)
            return True

        except Exception:
            self.ser = None
            self._put_status(f"● 等待串口连接：{self.port}", False)
            return False

    def _main_loop(self):
        while self.running:
            if self.ser is None or not self.ser.is_open:
                ok = self._open_serial()

                if not ok:
                    time.sleep(self.reconnect_interval)
                    continue

            try:
                self._read_loop()

            except Exception as e:
                self._put_status(f"● 串口异常，等待重连：{e}", False)

                try:
                    if self.ser and self.ser.is_open:
                        self.ser.close()
                except Exception:
                    pass

                self.ser = None
                time.sleep(self.reconnect_interval)

    def _read_loop(self):
        while self.running and self.ser and self.ser.is_open:
            line = self.ser.readline()

            if not line:
                continue

            try:
                line = line.decode("utf-8", errors="ignore").strip()
            except Exception:
                continue

            if not line:
                continue

            parts = line.split()

            if len(parts) == 514:
                pressure_parts = parts[:512]

                try:
                    posture_code = int(parts[512])
                except Exception:
                    posture_code = -1

                try:
                    button_flag = int(parts[513])
                except Exception:
                    button_flag = 0

            elif len(parts) == 513:
                pressure_parts = parts[:512]

                try:
                    posture_code = int(parts[512])
                except Exception:
                    posture_code = -1

                button_flag = 0

            elif len(parts) == 512:
                pressure_parts = parts
                posture_code = -1
                button_flag = 0

            else:
                continue

            try:
                values = [int(x) for x in pressure_parts]
            except ValueError:
                continue

            if len(values) != 512:
                continue

            matrix = np.array(values, dtype=np.int32).reshape(16, 32)

            peak_pressure = int(np.max(matrix))
            mean_pressure = float(np.mean(matrix))
            std_pressure = float(np.std(matrix))

            if posture_code == 7:
                is_seated = False
            elif posture_code in (0, 1, 2, 3, 4, 5, 6):
                is_seated = True
            else:
                is_seated = peak_pressure > SEATED_PEAK_THRESHOLD

            result = {
                "matrix": matrix,
                "posture_code": posture_code,
                "posture_name": POSTURE_MAP.get(posture_code, f"未知({posture_code})"),
                "button_flag": button_flag,
                "peak_pressure": peak_pressure,
                "mean_pressure": mean_pressure,
                "std_pressure": std_pressure,
                "is_seated": is_seated,
            }

            while self.data_queue.qsize() > 3:
                try:
                    self.data_queue.get_nowait()
                except Exception:
                    break

            self.data_queue.put(result)
            self._put_status(f"● 正在接收串口数据：{self.port}", True)