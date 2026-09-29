# serial_backend.py
import time
import threading
from queue import Queue

import serial
import numpy as np


POSTURE_MAP = {
    0: "端坐",
    1: "前倾",
    2: "后倾",
    3: "左倾",
    4: "右倾",
    5: "左腿离地二郎腿",
    6: "右腿离地二郎腿",
    7: "离座"
}


class SmartCushionSerialReceiver:
    """
    UI 统一串口接收器。

    支持：
    514 个整数：512 压力值 + pred + button_flag
    513 个整数：512 压力值 + pred
    512 个整数：只有压力矩阵
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

    def update_port(self, port, baudrate):
        self.port = port
        self.baudrate = baudrate

        try:
            if self.ser and self.ser.is_open:
                self.ser.close()
        except Exception:
            pass

        self.ser = None

    def _put_status(self, text, ok=False):
        try:
            self.status_queue.put({
                "text": text,
                "ok": ok
            })
        except Exception:
            pass

    def _open_serial(self):
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
            frame = self._parse_parts(parts)

            if frame is None:
                continue

            if self.data_queue.qsize() > 10:
                try:
                    self.data_queue.get_nowait()
                except Exception:
                    pass

            self.data_queue.put(frame)
            self._put_status(f"● 正在接收串口数据：{self.port}", True)

    def _parse_parts(self, parts):
        if len(parts) == 514:
            pressure_parts = parts[:512]
            pred_part = parts[512]
            button_part = parts[513]

        elif len(parts) == 513:
            pressure_parts = parts[:512]
            pred_part = parts[512]
            button_part = 0

        elif len(parts) == 512:
            pressure_parts = parts
            pred_part = None
            button_part = 0

        else:
            return None

        try:
            pressure_values = [int(x) for x in pressure_parts]
        except ValueError:
            return None

        if len(pressure_values) != 512:
            return None

        try:
            pred = int(pred_part) if pred_part is not None else None
        except Exception:
            pred = None

        try:
            button_flag = int(button_part)
        except Exception:
            button_flag = 0

        matrix = np.array(pressure_values, dtype=np.int32).reshape(16, 32)

        peak_pressure = int(np.max(matrix))
        mean_pressure = float(np.mean(matrix))
        std_pressure = float(np.std(matrix))

        if pred == 7:
            is_leave = True
            is_seated = False
        elif pred is None:
            is_leave = peak_pressure <= 300
            is_seated = peak_pressure > 300
        else:
            is_leave = False
            is_seated = True

        posture_name = POSTURE_MAP.get(pred, f"未知({pred})") if pred is not None else "--"

        return {
            "matrix": matrix,
            "pred": pred,
            "posture_code": pred,
            "posture_name": posture_name,
            "button_flag": button_flag,
            "peak_pressure": peak_pressure,
            "mean_pressure": mean_pressure,
            "std_pressure": std_pressure,
            "is_seated": is_seated,
            "is_leave": is_leave,
            "raw_count": len(parts)
        }