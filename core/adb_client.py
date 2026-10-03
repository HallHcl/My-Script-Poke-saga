import subprocess
import time
import random
import os
import cv2
import numpy as np

try:
    from ppadb.client import Client as PPADBClient
    HAS_PPADB = True
except ImportError:
    HAS_PPADB = False


class AdbClient:
    """Unified High-Speed ADB Controller for MuMuPlayer"""

    def __init__(self, adb_path: str = r"C:\Program Files\Netease\MuMuPlayer\nx_main\adb.exe",
                 device_serial: str = "127.0.0.1:5559"):
        self.adb_path = adb_path
        self.device_serial = device_serial
        self.ppadb_device = None
        self._init_connection()

    def _init_connection(self):
        """Try pure-python-adb socket connection first, fallback to CLI."""
        if HAS_PPADB:
            try:
                client = PPADBClient(host="127.0.0.1", port=5037)
                devices = client.devices()
                for dev in devices:
                    if dev.serial == self.device_serial or self.device_serial in dev.serial:
                        self.ppadb_device = dev
                        break
                if not self.ppadb_device and devices:
                    # If specific serial not found, use first available connected device
                    self.ppadb_device = devices[0]
            except Exception as e:
                self.ppadb_device = None

    def screencap(self) -> np.ndarray:
        """Capture screenshot and return as BGR numpy array (OpenCV format)."""
        # 1. Try PPADB Socket (Fastest)
        if self.ppadb_device:
            try:
                raw_bytes = self.ppadb_device.screencap()
                img = cv2.imdecode(np.frombuffer(raw_bytes, np.uint8), cv2.IMREAD_COLOR)
                if img is not None and img.shape[0] > 0:
                    return img
            except Exception:
                self.ppadb_device = None

        # 2. Subprocess Fallback
        cmd = [self.adb_path, "-s", self.device_serial, "exec-out", "screencap", "-p"]
        proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
        raw, _ = proc.communicate()
        img = cv2.imdecode(np.frombuffer(raw, np.uint8), cv2.IMREAD_COLOR)
        if img is None:
            raise RuntimeError("Failed to capture screenshot via ADB.")
        return img

    def tap(self, x: int, y: int, jitter: bool = True):
        """Tap at (x, y) with optional human jitter."""
        if jitter:
            x += random.randint(-3, 3)
            y += random.randint(-3, 3)

        if self.ppadb_device:
            try:
                self.ppadb_device.shell(f"input tap {x} {y}")
                return
            except Exception:
                self.ppadb_device = None

        subprocess.run([self.adb_path, "-s", self.device_serial, "shell", "input", "tap", str(x), str(y)],
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    def swipe(self, x1: int, y1: int, x2: int, y2: int, duration_ms: int = 300):
        """Simulate touch swipe."""
        cmd_str = f"input swipe {x1} {y1} {x2} {y2} {duration_ms}"
        if self.ppadb_device:
            try:
                self.ppadb_device.shell(cmd_str)
                return
            except Exception:
                self.ppadb_device = None

        subprocess.run([self.adb_path, "-s", self.device_serial, "shell", "input", "swipe",
                        str(x1), str(y1), str(x2), str(y2), str(duration_ms)],
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    def key_back(self):
        """Press Android Back Key (Keyevent 4)."""
        self.shell("input keyevent 4")

    def key_home(self):
        """Press Android Home Key (Keyevent 3)."""
        self.shell("input keyevent 3")

    def shell(self, command: str) -> str:
        """Run arbitrary shell command on the device."""
        if self.ppadb_device:
            try:
                return self.ppadb_device.shell(command) or ""
            except Exception:
                self.ppadb_device = None

        proc = subprocess.run([self.adb_path, "-s", self.device_serial, "shell"] + command.split(),
                              stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True)
        return proc.stdout or ""

    def is_package_running(self, package_name: str) -> bool:
        """Check if target game package is currently running."""
        out = self.shell(f"pidof {package_name}")
        return len(out.strip()) > 0

    def restart_app(self, package_name: str):
        """Force stop and launch the game."""
        self.shell(f"am force-stop {package_name}")
        time.sleep(1.0)
        self.shell(f"monkey -p {package_name} -c android.intent.category.LAUNCHER 1")
