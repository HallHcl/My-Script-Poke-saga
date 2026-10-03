import cv2  # type: ignore
import numpy as np
import subprocess
import time
import sys
import os
from datetime import datetime

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

# ============================================================
# CONFIG
# ============================================================

ADB = r"C:\Program Files\Netease\MuMuPlayer\nx_main\adb.exe"
DEVICE = "127.0.0.1:5559"

# Native game resolution = 1280x720 (240 DPI)
MATCH = (756, 662)

CHARACTERS = [
    (272, 654),
    (382, 654),
    (492, 654),
]

# Wave 1/2 Team Selection Next button
NEXT = (941, 492)

# Wave 3 Team Selection Battle start button
BATTLE = (941, 492)

# Battle Auto button (center: 56, 160; bbox approx [7, 111, 105, 209])
AUTO = (56, 160)

# Wave Result / Return button (center: 635, 633; bbox approx [564, 603, 707, 663])
RETURN = (635, 633)

MATCH_TIMEOUT = 130
BATTLE_LOADING_TIMEOUT = 60
BATTLE_TIMEOUT = 330         # 5 min 30 sec per wave (game timer: 5 min)
MATCH_MAX_TIMEOUT = 960      # 16 min emergency match circuit breaker (3 waves * 5 min + buffer)
MIN_BATTLE_TIME = 15
BATTLE_CHECK_INTERVAL = 3.5  # Check interval during battle (resource friendly: 3.5s)

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
MATCH_TEMPLATE = os.path.join(BASE_DIR, "templates", "match_button.png")
RETURN_TEMPLATE = os.path.join(BASE_DIR, "templates", "return_button.png")
NEXT_WAVE_TEMPLATE = os.path.join(BASE_DIR, "templates", "next_wave_button.png")
SCREENSHOT_DIR = os.path.join(BASE_DIR, "screenshots")

MATCH_THRESHOLD = 0.90
BUTTON_TYPE_THRESHOLD = 0.88
AUTO_YELLOW_THRESHOLD = 0.08
AUTO_BLUE_THRESHOLD = 0.25
RESULT_THRESHOLD = 0.25
REQUIRED_CONSECUTIVE_FRAMES = 2


# ============================================================
# ADB
# ============================================================

def ensure_device_connected(timeout=5):
    """
    Ensures ADB is connected to the emulator device.
    1. Checks 'adb -s <DEVICE> get-state'.
    2. If not 'device', attempts 'adb connect <DEVICE>'.
    3. Re-checks 'get-state'.
    4. Returns True if connected, False otherwise.
    """
    print()
    print("[ADB_CONNECTION]")
    print(f"    Checking connection to {DEVICE}...")

    def get_state():
        try:
            res = subprocess.run(
                [ADB, "-s", DEVICE, "get-state"],
                capture_output=True,
                text=True,
                timeout=timeout
            )
            return res.stdout.strip()
        except Exception:
            return ""

    # Check initial state
    state = get_state()
    if state == "device":
        print(f"    Device {DEVICE} is already connected.")
        return True

    print(f"    Device state: '{state or 'not found'}'. Attempting to connect...")
    try:
        connect_res = subprocess.run(
            [ADB, "connect", DEVICE],
            capture_output=True,
            text=True,
            timeout=timeout
        )
        print(f"    Connect response: {connect_res.stdout.strip()}")
    except Exception as e:
        print(f"    Connect error: {e}")
        return False

    time.sleep(1)

    # Re-check state after connect
    state = get_state()
    if state == "device":
        print(f"    Successfully connected to {DEVICE}.")
        return True

    print(f"    ERROR: Failed to connect to device {DEVICE} (state: '{state}').")
    return False


def adb(*args, capture=False):
    cmd = [
        ADB,
        "-s",
        DEVICE,
        *args
    ]

    if capture:
        return subprocess.check_output(cmd)

    subprocess.run(
        cmd,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL
    )


def screenshot():
    data = adb(
        "exec-out",
        "screencap",
        "-p",
        capture=True
    )

    img = cv2.imdecode(
        np.frombuffer(data, dtype=np.uint8),
        cv2.IMREAD_COLOR
    )

    if img is None:
        raise RuntimeError("Screenshot decode failed")

    return img


def tap(x, y):
    print(f"    TAP ({x},{y})")
    adb(
        "shell",
        "input",
        "tap",
        str(x),
        str(y)
    )


# ============================================================
# TEMPLATE MATCHING
# ============================================================

match_template = cv2.imread(MATCH_TEMPLATE)
return_template = cv2.imread(RETURN_TEMPLATE)
next_wave_template = cv2.imread(NEXT_WAVE_TEMPLATE)

if match_template is None:
    print()
    print("ERROR:")
    print(f"Template not found: {MATCH_TEMPLATE}")
    print()
    sys.exit(1)


def detect_match_button(img):
    result = cv2.matchTemplate(
        img,
        match_template,
        cv2.TM_CCOEFF_NORMED
    )
    _, confidence, _, location = cv2.minMaxLoc(result)
    return confidence, location


def detect_return_button(img):
    """Detects 'กลับ' text on the result button in bottom center region."""
    if return_template is None:
        return 0.0, None
    region = img[590:675, 550:720]
    res = cv2.matchTemplate(region, return_template, cv2.TM_CCOEFF_NORMED)
    _, max_val, _, max_loc = cv2.minMaxLoc(res)
    global_x = 550 + max_loc[0] + return_template.shape[1] // 2
    global_y = 590 + max_loc[1] + return_template.shape[0] // 2
    return float(max_val), (global_x, global_y)


def detect_next_wave_button(img):
    """Detects 'ต่อไป' text on the intermediate wave button in bottom center region."""
    if next_wave_template is None:
        return 0.0, None
    region = img[590:675, 550:720]
    res = cv2.matchTemplate(region, next_wave_template, cv2.TM_CCOEFF_NORMED)
    _, max_val, _, max_loc = cv2.minMaxLoc(res)
    global_x = 550 + max_loc[0] + next_wave_template.shape[1] // 2
    global_y = 590 + max_loc[1] + next_wave_template.shape[0] // 2
    return float(max_val), (global_x, global_y)


def has_countdown_text_below_button(img):
    """Checks for presence of white countdown text ('X วิ จะเริ่มรอบต่อไป') below button."""
    crop = img[670:715, 500:780]
    if crop is None or crop.size == 0:
        return False
    white_ratio = float(np.mean((crop[:, :, 0] > 180) & (crop[:, :, 1] > 180) & (crop[:, :, 2] > 180)))
    return white_ratio > 0.008


# ============================================================
# SCREEN DIFFERENCE & HSV ANALYSIS
# ============================================================

def screen_difference(img1, img2):
    diff = cv2.absdiff(img1, img2)
    return float(np.mean(diff))


def get_hsv_region(img, x, y, radius_x=45, radius_y=45):
    x1 = max(0, x - radius_x)
    y1 = max(0, y - radius_y)
    x2 = min(img.shape[1], x + radius_x)
    y2 = min(img.shape[0], y + radius_y)

    crop = img[y1:y2, x1:x2]
    if crop is None or crop.size == 0:
        return None

    return cv2.cvtColor(crop, cv2.COLOR_BGR2HSV)


def auto_blue_score(img, x=AUTO[0], y=AUTO[1]):
    """Detects blue/cyan color ratio around AUTO button (indicates AUTO OFF)."""
    hsv = get_hsv_region(img, x, y, 45, 45)
    if hsv is None:
        return 0.0

    lower = np.array([80, 50, 50])
    upper = np.array([135, 255, 255])
    mask = cv2.inRange(hsv, lower, upper)
    return float(np.mean(mask > 0))


def yellow_score(img, x=AUTO[0], y=AUTO[1]):
    """Detects yellow/gold color ratio around AUTO button (indicates AUTO ON)."""
    hsv = get_hsv_region(img, x, y, 45, 45)
    if hsv is None:
        return 0.0

    lower = np.array([10, 70, 80])
    upper = np.array([45, 255, 255])
    mask = cv2.inRange(hsv, lower, upper)
    return float(np.mean(mask > 0))


def detect_battle_screen(img):
    """
    Detects presence of the AUTO button in Battle screen.
    When Battle first appears: AUTO is OFF and the button is BLUE/CYAN.
    After clicking AUTO: the button becomes YELLOW/GOLD.
    Therefore, Battle detection detects whether the AUTO button exists
    in the region around (56, 160), regardless of whether it is OFF or ON.
    """
    blue = auto_blue_score(img, AUTO[0], AUTO[1])
    yellow = yellow_score(img, AUTO[0], AUTO[1])

    # Presence is confirmed if blue/cyan (OFF) or yellow (ON) button is present
    presence_score = max(blue, yellow)
    is_detected = (blue >= AUTO_BLUE_THRESHOLD) or (yellow >= AUTO_YELLOW_THRESHOLD)

    return is_detected, presence_score, blue, yellow


def result_button_score(img):
    """
    Detects gold/orange Return/Result button on the Result screen.
    Checks primary Result dialog / Summary button region around RETURN (635, 633).
    """
    hsv_center = get_hsv_region(img, RETURN[0], RETURN[1], 65, 45)
    if hsv_center is None:
        return 0.0
    mask_center = cv2.inRange(hsv_center, np.array([5, 60, 80]), np.array([45, 255, 255]))
    return float(np.mean(mask_center > 0))


# ============================================================
# STATE 1: MATCH BUTTON (LOBBY)
# ============================================================

def wait_for_match_button(timeout=30):
    print()
    print("[MATCH_BUTTON]")
    print("    Waiting for Match button...")

    start = time.time()
    while time.time() - start < timeout:
        img = screenshot()
        confidence, location = detect_match_button(img)
        print(f"    Confidence: {confidence:.4f}")

        if confidence >= MATCH_THRESHOLD:
            h, w = match_template.shape[:2]
            center_x = location[0] + w // 2
            center_y = location[1] + h // 2
            print(f"    Detected at ({center_x},{center_y})")
            return center_x, center_y

        # Auto-recovery: If screen is still on Result / Summary screen ("กลับ" button)
        ret_conf, _ = detect_return_button(img)
        if ret_conf >= BUTTON_TYPE_THRESHOLD or result_button_score(img) >= RESULT_THRESHOLD:
            print(f"    [RECOVERY] Result screen detected (conf={ret_conf:.3f}) -> Tapping 'กลับ' (635, 633)...")
            tap(RETURN[0], RETURN[1])
            time.sleep(2.0)
            continue

        time.sleep(1)

    return None


def start_match():
    result = wait_for_match_button()
    if result is None:
        print("ERROR: MATCH_BUTTON not detected")
        return False

    tap(*result)
    time.sleep(1)
    return True


# ============================================================
# STATE 2: MATCH SEARCHING
# ============================================================

def wait_for_match_result():
    print()
    print("[MATCH_SEARCHING]")
    print("    Waiting for opponent...")

    start = time.time()
    previous = screenshot()

    while time.time() - start < MATCH_TIMEOUT:
        current = screenshot()
        diff = screen_difference(previous, current)
        elapsed = int(time.time() - start)

        if diff > 8:
            print(f"    Screen changed (diff={diff:.2f})")
            # Give game time to render
            time.sleep(1)
            return True

        if elapsed > 0 and elapsed % 10 == 0:
            print(f"    Searching... {elapsed}s / {MATCH_TIMEOUT}s")

        previous = current
        time.sleep(1)

    print()
    print("ERROR: Matchmaking timeout")
    return False


# ============================================================
# STATE 3: TEAM SELECTION (WAVES 1, 2, 3)
# ============================================================

def select_team(wave):
    """
    Selects 3 characters for the specified wave.
    If wave < 3: taps NEXT to advance to the next wave team selection.
    If wave == 3: finishes character selection (BATTLE is tapped in run_bot).
    """
    print()
    print("=" * 60)
    print(f"TEAM SELECTION - WAVE {wave}")
    print("=" * 60)

    # 1. Select character 1
    print("    Selecting character 1")
    tap(CHARACTERS[0][0], CHARACTERS[0][1])
    time.sleep(0.3)

    # 2. Select character 2
    print("    Selecting character 2")
    tap(CHARACTERS[1][0], CHARACTERS[1][1])
    time.sleep(0.3)

    # 3. Select character 3
    print("    Selecting character 3")
    tap(CHARACTERS[2][0], CHARACTERS[2][1])
    time.sleep(0.5)

    # Advance to next wave team selection
    if wave < 3:
        print("    Clicking NEXT...")
        tap(NEXT[0], NEXT[1])
        time.sleep(1.5)


# ============================================================
# STATE 4: UNIFIED BATTLE LOOP
# ============================================================

def return_to_lobby(timeout=30):
    """Clicks Return on Final Result and waits until Lobby is confirmed."""
    print()
    print("[RETURN TO LOBBY]")
    print("    Clicking 'กลับ' (635, 633) to return to Lobby...")
    tap(RETURN[0], RETURN[1])

    start = time.time()
    time.sleep(1.5)
    last_tap_time = time.time()

    while time.time() - start < timeout:
        img = screenshot()
        match_conf, _ = detect_match_button(img)
        if match_conf >= MATCH_THRESHOLD:
            print("    Returned to Lobby successfully!")
            return True

        ret_conf, _ = detect_return_button(img)
        if ret_conf >= BUTTON_TYPE_THRESHOLD or result_button_score(img) >= RESULT_THRESHOLD:
            if time.time() - last_tap_time >= 1.5:
                print(f"    Result screen still visible (conf={ret_conf:.3f}) -> Tapping 'กลับ' again...")
                tap(RETURN[0], RETURN[1])
                last_tap_time = time.time()

        time.sleep(0.5)

    print("    Warning: Lobby confirmation timeout after Match")
    return False


def run_battle_loop(match_start_time):
    """
    Unified Battle Loop:
    1. Waits for initial Battle Scene to load after team selection.
    2. Continuously monitors the battle every BATTLE_CHECK_INTERVAL (3.5s):
       - If AUTO is Blue (new wave started or auto off) -> Taps AUTO to turn ON.
       - If 'กลับ' button appears (match finished) -> Taps 'กลับ' and returns to Lobby.
       - Ignores 'ต่อไป' between waves (game auto-advances in 5s).
    3. Handles 16-minute emergency watchdog circuit breaker.
    """
    print()
    print("=" * 60)
    print("[BATTLE PHASE - UNIFIED LOOP]")
    print("=" * 60)
    print("    Waiting for Battle Scene to load...")

    # Wait for initial battle load
    load_start = time.time()
    battle_loaded = False
    while time.time() - load_start < BATTLE_LOADING_TIMEOUT:
        img = screenshot()
        detected, score, blue, yellow = detect_battle_screen(img)
        if detected:
            print("    Battle scene loaded! Monitoring battle...")
            time.sleep(1.5)
            battle_loaded = True
            break
        time.sleep(1.0)

    if not battle_loaded:
        print("ERROR: Battle loading timeout.")
        save_debug_screenshot("battle_loading_failed")
        return False

    last_printed = -1
    last_auto_tap = 0
    consecutive_return_count = 0

    while True:
        # 1. Emergency Watchdog (16 minutes max per whole match)
        if time.time() - match_start_time > MATCH_MAX_TIMEOUT:
            print()
            print(f"    [MATCH GUARD] Match exceeded maximum limit ({MATCH_MAX_TIMEOUT}s / 16 min)!")
            print("    Triggering emergency recovery to Lobby...")
            tap(RETURN[0], RETURN[1])
            time.sleep(2.0)
            return False

        img = screenshot()
        elapsed = int(time.time() - match_start_time)

        # 2. Check if already in Lobby (e.g. opponent surrendered)
        match_conf, _ = detect_match_button(img)
        if match_conf >= MATCH_THRESHOLD:
            print()
            print(f"    Lobby detected (Match conf={match_conf:.4f}) -> Match completed!")
            return True

        # 3. Check for Match Finish ('กลับ' button)
        ret_conf, _ = detect_return_button(img)
        color_score = result_button_score(img)

        # Must have 'กลับ' template match AND golden button color
        if ret_conf >= BUTTON_TYPE_THRESHOLD and color_score >= RESULT_THRESHOLD:
            consecutive_return_count += 1
            print(f"    'กลับ' button detected (conf={ret_conf:.3f}, color={color_score:.3f} | count={consecutive_return_count}/{REQUIRED_CONSECUTIVE_FRAMES})")
            if consecutive_return_count >= REQUIRED_CONSECUTIVE_FRAMES:
                print()
                print("=" * 60)
                print("[MATCH FINISHED]")
                print("=" * 60)
                return return_to_lobby()
        else:
            consecutive_return_count = 0

        # 4. Check AUTO state (Blue = OFF -> Tap to enable)
        blue_val = auto_blue_score(img, AUTO[0], AUTO[1])
        yellow_val = yellow_score(img, AUTO[0], AUTO[1])

        if blue_val >= AUTO_BLUE_THRESHOLD and yellow_val < AUTO_YELLOW_THRESHOLD:
            if time.time() - last_auto_tap > 4.0:
                print(f"    [AUTO OFF (Blue={blue_val:.3f})] Tapping AUTO (56, 160) to enable...")
                tap(AUTO[0], AUTO[1])
                last_auto_tap = time.time()
                time.sleep(1.0)

        # 5. Clean periodic status log (every 15 seconds)
        if elapsed % 15 == 0 and elapsed != last_printed:
            auto_status = "ON (Yellow)" if yellow_val >= AUTO_YELLOW_THRESHOLD else ("OFF (Blue)" if blue_val >= AUTO_BLUE_THRESHOLD else "unknown")
            print(f"    Battle ongoing... Elapsed: {elapsed}s | AUTO: {auto_status}")
            last_printed = elapsed

        time.sleep(BATTLE_CHECK_INTERVAL)


# ============================================================
# DEBUG SCREENSHOT
# ============================================================

def save_debug_screenshot(prefix):
    try:
        os.makedirs(SCREENSHOT_DIR, exist_ok=True)
        img = screenshot()
        filename = os.path.join(
            SCREENSHOT_DIR,
            f"{datetime.now().strftime('%Y%m%d_%H%M%S')}_{prefix}.png"
        )
        cv2.imwrite(filename, img)
        print(f"    Debug screenshot saved: {filename}")
    except Exception as e:
        print(f"    Screenshot error: {e}")


# ============================================================
# MAIN BOT LOOP
# ============================================================

def run_bot():
    print()
    print("=" * 60)
    print("      MONSTER SAGA - CHAMPION BOT (บอทแชมป์)")
    print("=" * 60)
    print()
    print(f"Device:     {DEVICE}")
    print("Resolution: 1280x720 (240 DPI)")
    print("Mode:       ศึกแชมเปี้ยน (จับคู่ 3 Wave / ฟาร์มต่อเนื่อง)")
    print()
    print("CTRL+C = STOP")
    print()

    # Ensure ADB device is connected before entering match loop
    if not ensure_device_connected():
        print()
        print("=" * 60)
        print("ERROR: Device is not connected or emulator is not running.")
        print(f"Please verify MuMuPlayer is running at {DEVICE} and try again.")
        print("=" * 60)
        print()
        return

    match_count = 0

    while True:
        try:
            match_count += 1
            match_start_time = time.time()
            print()
            print("#" * 60)
            print(f"MATCH #{match_count} (Started at {datetime.now().strftime('%H:%M:%S')})")
            print("#" * 60)

            # -------------------------------------------------
            # 1. MATCH_BUTTON (Lobby)
            # -------------------------------------------------
            if not start_match():
                print("Could not start match.")
                time.sleep(2)
                continue

            # -------------------------------------------------
            # 2. MATCH_SEARCHING
            # -------------------------------------------------
            if not wait_for_match_result():
                print("Matchmaking failed.")
                save_debug_screenshot("matchmaking_timeout")
                continue

            # -------------------------------------------------
            # 3. TEAM SELECTION (Waves 1, 2, 3)
            # -------------------------------------------------
            # Select team 1 -> tap NEXT -> Select team 2 -> tap NEXT -> Select team 3
            select_team(1)
            select_team(2)
            select_team(3)

            # Tap BATTLE to start Match after selecting all 3 wave teams
            print()
            print("[TEAM SELECTION COMPLETE]")
            print("    Clicking BATTLE to start Match...")
            tap(BATTLE[0], BATTLE[1])
            time.sleep(2.0)

            # -------------------------------------------------
            # 4. BATTLE PHASE (Unified Battle Loop)
            # -------------------------------------------------
            battle_success = run_battle_loop(match_start_time)

            if not battle_success:
                print(f"MATCH #{match_count} encountered an error or timeout. Retrying next match...")
                continue

            # -------------------------------------------------
            # 5. MATCH COMPLETE -> LOOP
            # -------------------------------------------------
            elapsed_match = int(time.time() - match_start_time)
            print()
            print(f"MATCH #{match_count} COMPLETE (Duration: {elapsed_match // 60}m {elapsed_match % 60}s)")
            time.sleep(1)

        except KeyboardInterrupt:
            print()
            print()
            print("=" * 60)
            print("BOT STOPPED BY USER")
            print("=" * 60)
            print()
            break

        except Exception as e:
            print()
            print("=" * 60)
            print("UNEXPECTED ERROR")
            print("=" * 60)
            print(f"{type(e).__name__}: {e}")
            print()
            save_debug_screenshot("unexpected_error")
            print("Recovering in 3 seconds...")
            time.sleep(3)


# ============================================================
# START
# ============================================================

if __name__ == "__main__":
    run_bot()