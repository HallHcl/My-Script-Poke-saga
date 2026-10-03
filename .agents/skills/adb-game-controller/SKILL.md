---
name: adb-game-controller
description: >-
  Expert guide for Android game bot automation via ADB. Covers high-speed screencaps,
  human-like input simulation (tap, swipe), process recovery, MuMuPlayer port management,
  and socket-based ADB communication.
---

# ADB Game Controller Skill

## 1. Environment & Target Specs
- **Emulator**: MuMuPlayer (Netease)
- **Default ADB Port**: `127.0.0.1:5559`
- **Fallback ADB Executable**: `C:\Program Files\Netease\MuMuPlayer\nx_main\adb.exe`
- **Target Resolution**: `1280 x 720` (Native DPI: 240)

## 2. High-Performance Input & Screen Capture

### Screencap via Pure-Python-ADB (Socket) vs Subprocess
1. **Socket Stream (Fastest)**:
   ```python
   from ppadb.client import Client as AdbClient
   client = AdbClient(host="127.0.0.1", port=5037)
   device = client.device("127.0.0.1:5559")
   raw_bytes = device.screencap()
   # Decode via cv2:
   import cv2, numpy as np
   img = cv2.imdecode(np.frombuffer(raw_bytes, np.uint8), cv2.IMREAD_COLOR)
   ```
2. **Subprocess Pipe (Reliable Fallback)**:
   ```python
   import subprocess, cv2, numpy as np
   cmd = [ADB_PATH, "-s", DEVICE, "exec-out", "screencap", "-p"]
   proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
   raw, _ = proc.communicate()
   img = cv2.imdecode(np.frombuffer(raw, np.uint8), cv2.IMREAD_COLOR)
   ```

### Human-like Touch Simulation
To prevent anti-cheat pattern detection:
- Add slight jitter (e.g. `x + random.randint(-4, 4)`, `y + random.randint(-4, 4)`).
- Variable touch duration (`input swipe x y x y duration_ms`).
- For taps: randomized sleep (`time.sleep(random.uniform(0.15, 0.35))`).

## 3. Process Lifecycle & Crash Recovery
- **Kill App**: `adb shell am force-stop <package_name>`
- **Launch App**: `adb shell monkey -p <package_name> -c android.intent.category.LAUNCHER 1`
- **Back Key**: `adb shell input keyevent 4`
- **Home Key**: `adb shell input keyevent 3`
- **Check Process Alive**: `adb shell pidof <package_name>`
