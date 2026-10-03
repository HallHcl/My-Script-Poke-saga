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
# CONFIG (Season 2 Pattern: 1-Char Wave 1 Manual, 2-Char Wave 2, 3-Char Wave 3)
# ============================================================

ADB = r"C:\Program Files\Netease\MuMuPlayer\nx_main\adb.exe"
DEVICE = "127.0.0.1:5559"

# Native game resolution = 1280x720 (240 DPI)
MATCH = (756, 662)

CHARACTERS = [
    (205, 670),  # Character 1 (Groudon)
    (305, 670),  # Character 2 (Charizard X)
    (405, 670),  # Character 3 (Gengar)
]

# Wave 1/2 Team Selection Next button (Blue hexagon)
NEXT = (940, 490)

# Wave 3 Team Selection Battle start button
BATTLE = (940, 490)

# Battle Auto button (center: 45, 240)
AUTO = (45, 240)

# Wave 1 Manual Skills: Red skill first, then Green skill
SKILL_RED = (708, 627)    # Skill in Red Box (Meteor / Fire)
SKILL_GREEN = (956, 625)  # Skill in Green Box (Claws / Slash)

# Wave Result / Return button (center: 635, 633; bbox approx [564, 603, 707, 663])
RETURN = (635, 633)

MATCH_TIMEOUT = 130
BATTLE_LOADING_TIMEOUT = 60
BATTLE_TIMEOUT = 330         # 5 min 30 sec per wave (game timer: 5 min)
MATCH_MAX_TIMEOUT = 960      # 16 min emergency match circuit breaker (3 waves * 5 min + buffer)
MIN_BATTLE_TIME = 15
BATTLE_CHECK_INTERVAL = 1.5  # Check interval during battle (Wave 1 manual responsiveness)

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
MATCH_TEMPLATE = os.path.join(BASE_DIR, "templates", "match_button.png")
RETURN_TEMPLATE = os.path.join(BASE_DIR, "templates", "return_button.png")
NEXT_WAVE_TEMPLATE = os.path.join(BASE_DIR, "templates", "next_wave_button.png")
SCREENSHOT_DIR = os.path.join(BASE_DIR, "screenshots")

MATCH_THRESHOLD = 0.90
BUTTON_TYPE_THRESHOLD = 0.88
AUTO_YELLOW_THRESHOLD = 0.15
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
        print(f"    connect output: {connect_res.stdout.strip()}")
    except Exception as e:
        print(f"    Connection attempt failed: {e}")
        return False

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

    return img


def tap(x, y):
    adb(
        "shell",
        "input",
        "tap",
        str(x),
        str(y)
    )


def save_debug_screenshot(prefix="debug"):
    try:
        os.makedirs(SCREENSHOT_DIR, exist_ok=True)
        img = screenshot()
        if img is not None:
            filename = os.path.join(
                SCREENSHOT_DIR,
                f"{datetime.now().strftime('%Y%m%d_%H%M%S')}_{prefix}.png"
            )
            cv2.imwrite(filename, img)
            print(f"    Debug screenshot saved: {filename}")
    except Exception as e:
        print(f"    Failed to save debug screenshot: {e}")


# ============================================================
# TEMPLATE MATCHING & VISION
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


def get_hsv_region(img, x, y, radius_x=35, radius_y=35):
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
    hsv = get_hsv_region(img, x, y, 35, 35)
    if hsv is None:
        return 0.0

    lower = np.array([80, 50, 50])
    upper = np.array([135, 255, 255])
    mask = cv2.inRange(hsv, lower, upper)
    return float(np.mean(mask > 0))


def auto_yellow_score(img, x=AUTO[0], y=AUTO[1]):
    """Detects gold/yellow color ratio around AUTO button (indicates AUTO ON)."""
    hsv = get_hsv_region(img, x, y, 35, 35)
    if hsv is None:
        return 0.0

    lower = np.array([15, 80, 80])
    upper = np.array([35, 255, 255])
    mask = cv2.inRange(hsv, lower, upper)
    return float(np.mean(mask > 0))


def result_button_score(img):
    """
    Detects the presence of the golden-orange Result Button at (635, 633).
    Returns ratio of pixels in the gold/orange color range.
    """
    hsv = get_hsv_region(img, RETURN[0], RETURN[1], 45, 25)
    if hsv is None:
        return 0.0

    lower = np.array([10, 100, 100])
    upper = np.array([30, 255, 255])
    mask = cv2.inRange(hsv, lower, upper)
    return float(np.mean(mask > 0))


def detect_battle_screen(img):
    """
    Determines if the game is currently inside the battle screen.
    Returns: (is_battle: bool, score: float, blue_score: float, yellow_score: float)
    """
    blue = auto_blue_score(img)
    yellow = auto_yellow_score(img)
    score = max(blue, yellow)
    threshold = AUTO_YELLOW_THRESHOLD if yellow > blue else AUTO_BLUE_THRESHOLD
    is_battle = score >= threshold
    return is_battle, score, blue, yellow


# ============================================================
# STATE 1: LOBBY & MATCH START
# ============================================================

def wait_for_lobby():
    print()
    print("[LOBBY]")
    print("    Checking if on result screen...")

    start = time.time()
    while time.time() - start < 15:
        img = screenshot()
        match_conf, _ = detect_match_button(img)

        if match_conf >= MATCH_THRESHOLD:
            print("    Lobby confirmed (Match button ready).")
            return True

        ret_conf, _ = detect_return_button(img)
        btn_score = result_button_score(img)

        if ret_conf >= BUTTON_TYPE_THRESHOLD or btn_score >= RESULT_THRESHOLD:
            print(f"    Stuck on result screen (conf={ret_conf:.3f}, color={btn_score:.3f}) -> Tapping 'กลับ' (635, 633)...")
            tap(RETURN[0], RETURN[1])
            time.sleep(2.0)
            continue

        time.sleep(1.0)

    print("    Waiting for MATCH button in Lobby...")
    while True:
        img = screenshot()
        confidence, location = detect_match_button(img)

        if confidence >= MATCH_THRESHOLD:
            print(f"    MATCH button detected (confidence={confidence:.4f})")
            return True

        ret_conf, _ = detect_return_button(img)
        btn_score = result_button_score(img)
        if ret_conf >= BUTTON_TYPE_THRESHOLD or btn_score >= RESULT_THRESHOLD:
            print(f"    Result button still visible -> Tapping 'กลับ' (635, 633)...")
            tap(RETURN[0], RETURN[1])
            time.sleep(2.0)

        time.sleep(1)


def start_match():
    if not wait_for_lobby():
        return False

    print("    Clicking MATCH...")
    tap(MATCH[0], MATCH[1])
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
            time.sleep(0.6)
            return True

        if elapsed > 0 and elapsed % 10 == 0:
            print(f"    Searching... {elapsed}s / {MATCH_TIMEOUT}s")

        previous = current
        time.sleep(1)

    print()
    print("ERROR: Matchmaking timeout")
    return False


# ============================================================
# STATE 3: TEAM SELECTION (SEASON 2: 1-CHAR, 2-CHAR, 3-CHAR)
# ============================================================

def select_team(wave):
    """
    Season 2 Team Selection (High-Speed Turbo):
    - Wave 1: 1 character (Character 1) -> tap NEXT
    - Wave 2: 2 characters (Characters 1, 2) -> tap NEXT
    - Wave 3: 3 characters (Characters 1, 2, 3) -> finishes selection (BATTLE tapped in run_bot)
    """
    print()
    print("=" * 60)
    print(f"TEAM SELECTION - WAVE {wave} (Season 2 Pattern)")
    print("=" * 60)

    num_chars = wave  # Wave 1 = 1 char, Wave 2 = 2 chars, Wave 3 = 3 chars
    print(f"    [Fast Selection] Selecting {num_chars} character(s) for Wave {wave}...")

    for i in range(num_chars):
        char_x, char_y = CHARACTERS[i]
        print(f"    Selecting character {i + 1} at ({char_x}, {char_y})")
        tap(char_x, char_y)
        time.sleep(0.12)

    time.sleep(0.15)

    if wave < 3:
        print("    Clicking NEXT (940, 490)...")
        tap(NEXT[0], NEXT[1])
        time.sleep(0.65)


# ============================================================
# STATE 4: UNIFIED BATTLE LOOP (SEASON 2: WAVE 1 MANUAL, WAVE 2-3 AUTO)
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
    Season 2 Unified Battle Loop:
    - Wave 1: Manual combat. DO NOT press AUTO.
              Repeatedly taps skill buttons (Ult -> Skill 3 -> Skill 2 -> Normal).
              If Auto is detected ON, forcibly turns it OFF.
    - Wave Transition: When 'ต่อไป' or intermediate result countdown appears,
                       increments wave counter (Wave 1 -> Wave 2 -> Wave 3).
    - Wave 2 & 3: AUTO combat allowed.
                  Taps AUTO (55, 255) to turn ON whenever it is blue (OFF).
    - Final Result: Detects 'กลับ' (635, 633) for 2 consecutive frames -> exits to Lobby.
    - 16-Minute emergency watchdog protection.
    """
    print()
    print("=" * 60)
    print("[BATTLE PHASE - SEASON 2 LOOP]")
    print("=" * 60)
    print("    Waiting for Battle Scene to load...")

    # Wait for initial battle load
    load_start = time.time()
    battle_loaded = False
    while time.time() - load_start < BATTLE_LOADING_TIMEOUT:
        img = screenshot()
        detected, score, blue, yellow = detect_battle_screen(img)
        if detected:
            print(f"    Battle scene loaded! (blue={blue:.3f}, yellow={yellow:.3f})")
            time.sleep(1.5)
            battle_loaded = True
            break
        time.sleep(1.0)

    if not battle_loaded:
        print("ERROR: Battle loading timeout.")
        save_debug_screenshot("battle_loading_failed")
        return False

    current_wave = 1
    last_printed = -1
    last_auto_tap = 0
    consecutive_return_count = 0

    print(f"\n    >>> Starting Wave {current_wave} (Manual Combat - No Auto) <<<")

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

        # 3. Check for Final Match Finish ('กลับ' button)
        ret_conf, _ = detect_return_button(img)
        color_score = result_button_score(img)

        if ret_conf >= BUTTON_TYPE_THRESHOLD and color_score >= RESULT_THRESHOLD:
            consecutive_return_count += 1
            print(f"    'กลับ' button detected (conf={ret_conf:.3f}, color={color_score:.3f} | count={consecutive_return_count}/{REQUIRED_CONSECUTIVE_FRAMES})")
            if consecutive_return_count >= REQUIRED_CONSECUTIVE_FRAMES:
                print("    Final Match Result Confirmed!")
                return return_to_lobby()
            time.sleep(0.5)
            continue
        else:
            consecutive_return_count = 0

        # 4. Check for Next Wave button (intermediate wave victory)
        next_conf, _ = detect_next_wave_button(img)
        has_countdown = has_countdown_text_below_button(img)

        if next_conf >= BUTTON_TYPE_THRESHOLD or (color_score >= RESULT_THRESHOLD and has_countdown):
            print(f"    'ต่อไป' button detected (conf={next_conf:.3f}) - Wave {current_wave} completed!")
            current_wave += 1
            if current_wave <= 3:
                print(f"    >>> Advancing to Wave {current_wave} (Auto combat enabled) <<<")
            print("    Letting game countdown auto-advance to next wave (5s)...")
            time.sleep(4.0)
            continue

        # 5. Combat Action during Wave
        blue_score = auto_blue_score(img)
        yellow_score = auto_yellow_score(img)

        if current_wave == 1:
            # Wave 1: STRICTLY MANUAL COMBAT
            # Check if AUTO is accidentally ON -> Turn it OFF
            if yellow_score >= AUTO_YELLOW_THRESHOLD:
                if time.time() - last_auto_tap >= 5:
                    print(f"    [Wave 1 Rule] Auto is ON (yellow={yellow_score:.3f}) -> Tapping AUTO to turn OFF...")
                    tap(AUTO[0], AUTO[1])
                    last_auto_tap = time.time()
                    time.sleep(0.5)

            # Manually trigger skills in Wave 1: Red skill first, then Green skill
            tap(SKILL_RED[0], SKILL_RED[1])
            time.sleep(0.20)
            tap(SKILL_GREEN[0], SKILL_GREEN[1])
            time.sleep(0.20)

            if elapsed - last_printed >= 5:
                print(f"    [Wave 1 Manual] Fighting... Elapsed: {elapsed}s | Auto: OFF")
                last_printed = elapsed

        else:
            # Wave 2 & Wave 3: AUTO COMBAT ALLOWED
            if blue_score >= AUTO_BLUE_THRESHOLD:
                if time.time() - last_auto_tap >= 8:
                    print(f"    [Wave {current_wave}] AUTO is OFF (blue={blue_score:.3f}) -> Tapping AUTO (45, 240) to turn ON...")
                    tap(AUTO[0], AUTO[1])
                    last_auto_tap = time.time()
                    time.sleep(1.0)
            elif yellow_score >= AUTO_YELLOW_THRESHOLD:
                if elapsed - last_printed >= 10:
                    print(f"    [Wave {current_wave} Auto] In battle... Elapsed: {elapsed}s (Auto: ON)")
                    last_printed = elapsed

        time.sleep(BATTLE_CHECK_INTERVAL)


# ============================================================
# MAIN BOT RUNNER
# ============================================================

def run_bot():
    print()
    print("=" * 60)
    print("MONSTER SAGA BOT - ศึกแชมเปี้ยน SEASON 2")
    print("=" * 60)
    print(f"Device:     {DEVICE}")
    print(f"ADB:        {ADB}")
    print("Resolution: 1280x720 (Native)")
    print("Mode:       ศึกแชมเปี้ยน Season 2 (Wave 1: 1ตัว Manual | Wave 2: 2ตัว Auto | Wave 3: 3ตัว Auto)")
    print()
    print("CTRL+C = STOP")
    print()

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
            print(f"MATCH #{match_count} [Season 2] (Started at {datetime.now().strftime('%H:%M:%S')})")
            print("#" * 60)

            # 1. MATCH_BUTTON (Lobby)
            if not start_match():
                print("Could not start match.")
                time.sleep(2)
                continue

            # 2. MATCH_SEARCHING
            if not wait_for_match_result():
                print("Matchmaking failed.")
                save_debug_screenshot("matchmaking_timeout")
                continue

            # 3. TEAM SELECTION (Waves 1, 2, 3)
            # Season 2: Wave 1 selects 1, Wave 2 selects 2, Wave 3 selects 3
            select_team(1)
            select_team(2)
            select_team(3)

            # Tap BATTLE to start Match after selecting all 3 wave teams
            print()
            print("[TEAM SELECTION COMPLETE]")
            print("    Clicking BATTLE to start Match...")
            tap(BATTLE[0], BATTLE[1])
            time.sleep(2.0)

            # 4. BATTLE PHASE (Season 2 Loop)
            battle_success = run_battle_loop(match_start_time)

            if not battle_success:
                print(f"MATCH #{match_count} encountered an error or timeout. Retrying next match...")
                continue

            # 5. MATCH COMPLETE -> LOOP
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
