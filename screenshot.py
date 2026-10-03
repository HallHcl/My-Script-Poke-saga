#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
MonsterBot Screenshot Utility
=============================
สคริปต์แคปภาพหน้าจอเกมผ่าน ADB (MuMuPlayer)
บันทึกภาพลงใน screenshots/ อัตโนมัติ รองรับการใส่ prefix หรือชื่อไฟล์
"""

import os
import sys
import argparse
from datetime import datetime
from pathlib import Path
import cv2

# Configuration
BASE_DIR = Path(__file__).resolve().parent
SCREENSHOT_DIR = BASE_DIR / "screenshots"
SCREENSHOT_DIR.mkdir(parents=True, exist_ok=True)

# Add project root to sys.path to import core modules
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

try:
    from core.adb_client import AdbClient
except ImportError:
    AdbClient = None


def take_screenshot(prefix: str = "screen", custom_name: str = None) -> Path:
    """แคปภาพหน้าจอจาก ADB และบันทึกไฟล์"""
    # 1. Connect ADB Client
    if AdbClient:
        client = AdbClient()
        img = client.screencap()
    else:
        # Fallback to direct adb subprocess
        import subprocess
        import numpy as np
        cmd = [r"C:\Program Files\Netease\MuMuPlayer\nx_main\adb.exe", "-s", "127.0.0.1:5559", "exec-out", "screencap", "-p"]
        proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
        raw, _ = proc.communicate()
        img = cv2.imdecode(np.frombuffer(raw, np.uint8), cv2.IMREAD_COLOR)

    if img is None:
        print("[ERROR] ไม่สามารถจับภาพหน้าจอจาก ADB ได้ (กรุณาตรวจสอบว่า MuMuPlayer เปิดอยู่หรือไม่)")
        return None

    # 2. Generate filename
    if custom_name:
        filename = custom_name if custom_name.endswith(".png") else f"{custom_name}.png"
    else:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{timestamp}_{prefix}.png"

    output_path = SCREENSHOT_DIR / filename
    cv2.imwrite(str(output_path), img)
    print(f"[OK] Screenshot saved: {output_path} ({img.shape[1]}x{img.shape[0]})")
    return output_path


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Capture MonsterBot screenshot via ADB")
    parser.add_argument("--prefix", "-p", default="screen", help="Filename prefix (default: screen)")
    parser.add_argument("--name", "-n", default=None, help="Exact custom filename")
    args = parser.parse_args()

    take_screenshot(prefix=args.prefix, custom_name=args.name)