import sys
import cv2  # type: ignore
import numpy as np
import subprocess
import time
import os
from datetime import datetime
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace", line_buffering=True)

# ============================================================
# CONFIG & DEVICE
# ============================================================

ADB = r"C:\Program Files\Netease\MuMuPlayer\nx_main\adb.exe"
DEVICE = "127.0.0.1:5559"
BASE_DIR = Path(__file__).resolve().parent.parent.parent
SCREENSHOT_DIR = BASE_DIR / "screenshots"
SCREENSHOT_DIR.mkdir(parents=True, exist_ok=True)
DAILY_RECORD_FILE = Path(__file__).resolve().parent / "tower_daily_done.txt"
TPL_FLOOR_80 = BASE_DIR / "templates" / "badge_floor_80.png"
TPL_FLOOR_80_NORMAL = BASE_DIR / "templates" / "badge_normal_80.png"
TPL_DIGIT_8 = BASE_DIR / "templates" / "digit_8.png"
TPL_DIGIT_0 = BASE_DIR / "templates" / "digit_0.png"

# ============================================================
# VERIFIED COORDINATES (1280x720 Native Resolution)
# ============================================================

# 1. Opponent Battle
OPPONENT = (707, 520)           # Click enemy standing in center
CHALLENGE_HARD = (988, 471)     # Hard Challenge (Purple)

# In-Battle Controls
AUTO_TOWER = (52, 255)          # "ต่อสู้ออโต้" button in Tower battle
VICTORY_NEXT = (800, 630)       # "ต่อไป" button on victory screen (must tap, countdown is bugged)

# 2. Buff Station
BUFF_EMBLEM = (706, 586)        # Pokeball emblem on buff platform
BUY_BUFF_RIGHT = (940, 540)     # Attack Buff (Atk +15%)
BUFF_CLOSE_X = (1230, 43)       # Close button on "ซื้อbuff"
BUFF_CONFIRM_OK = (717, 411)    # "ตกลง" button on warning popup ("ยังมีbuffไม่ได้ซื้อ จะปิดไหม")

# 3. Treasure Chest
CHEST_TARGET = (707, 600)       # Click golden chest in center
CHEST_DISMISS = (500, 660)      # "คลิกรับรางวัล" text to dismiss reward
CHEST_LEAVE = (430, 575)        # "ทิ้งไว้" button to avoid spending 20 diamonds (Center verified)


# ============================================================
# ADB HELPERS
# ============================================================

def ensure_device_connected(timeout=5):
    try:
        res = subprocess.run([ADB, "-s", DEVICE, "get-state"], capture_output=True, text=True, timeout=timeout)
        if res.stdout.strip() == "device":
            return True
        subprocess.run([ADB, "connect", DEVICE], capture_output=True, text=True, timeout=timeout)
        time.sleep(1)
        res = subprocess.run([ADB, "-s", DEVICE, "get-state"], capture_output=True, text=True, timeout=timeout)
        return res.stdout.strip() == "device"
    except Exception:
        return False


def adb(*args, capture=False):
    ensure_device_connected()
    cmd = [ADB, "-s", DEVICE, *args]
    if capture:
        return subprocess.check_output(cmd)
    subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


def screenshot(save=False, prefix="tower"):
    data = adb("exec-out", "screencap", "-p", capture=True)
    img = cv2.imdecode(np.frombuffer(data, dtype=np.uint8), cv2.IMREAD_COLOR)
    if save and img is not None:
        filename = datetime.now().strftime(f"%Y%m%d_%H%M%S_{prefix}.png")
        cv2.imwrite(str(SCREENSHOT_DIR / filename), img)
    return img


def tap(x, y):
    print(f"    TAP ({x}, {y})")
    adb("shell", "input", "tap", str(x), str(y))


# ============================================================
# DETECTION HELPERS
# ============================================================

def is_in_tower_lobby(img):
    """Checks if currently in Tower lobby screen (orange arrow present)."""
    if img is None:
        return False
    b, g, r = cv2.split(img)
    arrow_mask = (r > 200) & (g > 100) & (g < 190) & (b < 50)
    cnt = np.count_nonzero(arrow_mask[400:500, 680:750])
    return cnt > 150


def is_tower_auto_off(img):
    """Checks if 'ต่อสู้ออโต้' button is visible (meaning AUTO is currently OFF)."""
    if img is None:
        return False
    crop = img[210:300, 10:95]
    b, g, r = cv2.split(crop)
    cyan = (b > 180) & (g > 180) & (r < 100)
    return np.count_nonzero(cyan) > 200


def is_select_opponent_open(img):
    """Checks if 'เลือกคู่แข่ง' popup is open (cyan title at top)."""
    if img is None or img.shape[:2] != (720, 1280):
        return False
    crop = img[20:70, 520:760]
    hsv = cv2.cvtColor(crop, cv2.COLOR_BGR2HSV)
    cyan = cv2.inRange(hsv, np.array([85, 100, 150]), np.array([105, 255, 255]))
    return np.count_nonzero(cyan) > 2000


def is_victory_screen(img):
    """
    Checks if victory screen is visible:
    - Yellow 'ต่อไป' button at (730:860, 600:660)
    - Yellow 'กลับ' button at (430:560, 600:660)
    - Golden 'ชนะการต่อสู้' victory banner at (400:880, 80:200)
    This prevents false positives from popup screens like 'เลือกคู่แข่ง'.
    """
    if img is None or img.shape[:2] != (720, 1280):
        return False
    hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
    btn_next = cv2.inRange(hsv[600:660, 730:860], np.array([12, 100, 150]), np.array([28, 255, 255]))
    btn_back = cv2.inRange(hsv[600:660, 430:560], np.array([12, 100, 150]), np.array([28, 255, 255]))
    banner_mask = cv2.inRange(hsv[80:200, 400:880], np.array([12, 120, 180]), np.array([25, 255, 255]))
    return np.count_nonzero(btn_next) > 2000 and np.count_nonzero(btn_back) > 2000 and np.count_nonzero(banner_mask) > 3000


def is_at_floor_80(img):
    """
    Checks if currently on Floor 80:
    1. Must be in Tower Lobby
    2. Isolates yellow text from floor badge crop (365:405, 80:150)
    3. Verifies presence of digit '8' AND digit '0' via template matching (> 0.88 each)
       Compatible with both Normal Mode (blue badge) and Hard Mode (red badge).
    """
    if not is_in_tower_lobby(img):
        return False

    crop = img[365:405, 80:150]
    hsv = cv2.cvtColor(crop, cv2.COLOR_BGR2HSV)
    yellow_mask = cv2.inRange(hsv, np.array([15, 100, 150]), np.array([35, 255, 255]))

    if np.count_nonzero(yellow_mask) < 150:
        return False

    if TPL_DIGIT_8.exists() and TPL_DIGIT_0.exists():
        tpl_8 = cv2.imread(str(TPL_DIGIT_8), cv2.IMREAD_GRAYSCALE)
        tpl_0 = cv2.imread(str(TPL_DIGIT_0), cv2.IMREAD_GRAYSCALE)
        if tpl_8 is not None and tpl_0 is not None:
            res_8 = cv2.matchTemplate(yellow_mask, tpl_8, cv2.TM_CCOEFF_NORMED)
            res_0 = cv2.matchTemplate(yellow_mask, tpl_0, cv2.TM_CCOEFF_NORMED)
            if res_8.max() > 0.88 and res_0.max() > 0.88:
                return True

    return False


def detect_floor_type(img):
    """
    Accurately detects whether the active target is:
    - 'OPPONENT': Character with head present under arrow
    - 'BUFF': Glowing cyan emblem on platform
    - 'CHEST': Golden treasure chest
    - 'TRANSITION': Platform/character still moving or elevator in transit
    """
    if img is None or img.shape[:2] != (720, 1280):
        return "UNKNOWN"

    # 1. Check if Opponent Head is present right below arrow
    head_crop = img[480:540, 675:740]
    gray_head = cv2.cvtColor(head_crop, cv2.COLOR_BGR2GRAY)
    if gray_head.mean() > 40:
        return "OPPONENT"

    # 2. Distinguish between BUFF and CHEST
    crop_center = img[520:640, 660:750]
    b, g, r = cv2.split(crop_center)
    cyan_count = np.count_nonzero((b > 180) & (g > 180) & (r < 150))
    gold_count = np.count_nonzero((r > 180) & (g > 150) & (b < 100))

    if cyan_count > 300:
        return "BUFF"
    elif gold_count > 200:
        return "CHEST"

    return "TRANSITION"


# ============================================================
# ACTIONS
# ============================================================

def do_battle():
    """Handles opponent selection, enters battle, enables auto, and taps next on victory."""
    img = screenshot()
    if not is_select_opponent_open(img):
        print("[TOWER BATTLE] 1. Tapping opponent...")
        tap(OPPONENT[0], OPPONENT[1])
        # Wait up to 3s for select opponent popup to appear
        for _ in range(6):
            time.sleep(0.5)
            img = screenshot()
            if is_select_opponent_open(img):
                break

    print("[TOWER BATTLE] 2. Selecting Hard Challenge (Purple)...")
    tap(CHALLENGE_HARD[0], CHALLENGE_HARD[1])
    time.sleep(2.0)

    # Wait for battle and handle AUTO
    print("[TOWER BATTLE] 3. Monitoring battle...")
    start_wait = time.time()
    last_auto_tap = 0
    in_battle = False

    while time.time() - start_wait < 90:
        time.sleep(2.0)
        img = screenshot()

        # Check if select opponent popup is still open (tap might have missed or animation delay)
        if not in_battle and is_select_opponent_open(img):
            print("    [POPUP STILL OPEN] Re-tapping Challenge Hard...")
            tap(CHALLENGE_HARD[0], CHALLENGE_HARD[1])
            time.sleep(2.0)
            continue

        # Check if victory screen appeared
        if is_victory_screen(img):
            print("[TOWER BATTLE] Victory screen detected! Tapping 'ต่อไป' (800, 630)...")
            tap(VICTORY_NEXT[0], VICTORY_NEXT[1])
            time.sleep(3.0)
            return True

        # Check if returned to Tower lobby already
        if time.time() - start_wait > 5.0 and is_in_tower_lobby(img):
            print("[TOWER BATTLE] Already back in Tower Lobby!")
            return True

        # Check if AUTO is OFF in battle -> Tap to turn ON
        if is_tower_auto_off(img):
            in_battle = True
            if time.time() - last_auto_tap > 4.0:
                print("    [AUTO OFF] Tapping AUTO (52, 255)...")
                tap(AUTO_TOWER[0], AUTO_TOWER[1])
                last_auto_tap = time.time()

    print("[TOWER BATTLE] Warning: Battle timed out.")
    return False


def do_buy_buff():
    """Clicks buff platform, buys Attack buff on right, and confirms close."""
    print("[TOWER BUFF] 1. Clicking buff emblem...")
    tap(BUFF_EMBLEM[0], BUFF_EMBLEM[1])
    time.sleep(2.0)

    print("[TOWER BUFF] 2. Buying right buff (Attack)...")
    tap(BUY_BUFF_RIGHT[0], BUY_BUFF_RIGHT[1])
    time.sleep(1.5)

    print("[TOWER BUFF] 3. Closing buff popup...")
    tap(BUFF_CLOSE_X[0], BUFF_CLOSE_X[1])
    time.sleep(1.5)

    print("[TOWER BUFF] 4. Confirming warning popup ('ตกลง')...")
    tap(BUFF_CONFIRM_OK[0], BUFF_CONFIRM_OK[1])
    time.sleep(2.0)
    return True


def do_collect_chest():
    """Clicks chest, collects free rewards, and taps 'ทิ้งไว้' to save diamonds."""
    print("[TOWER CHEST] 1. Opening treasure chest...")
    tap(CHEST_TARGET[0], CHEST_TARGET[1])
    time.sleep(2.0)

    print("[TOWER CHEST] 2. Dismissing reward popup...")
    tap(CHEST_DISMISS[0], CHEST_DISMISS[1])
    time.sleep(1.5)

    print("[TOWER CHEST] 3. Tapping 'ทิ้งไว้' to skip spending diamonds...")
    tap(CHEST_LEAVE[0], CHEST_LEAVE[1])
    time.sleep(2.0)
    return True


# ============================================================
# DAILY LIMIT SYSTEM (เกมรีเซ็ตทุกตี 5 / 05:00 AM)
# ============================================================

def get_game_date():
    """
    Returns the game cycle date (YYYY-MM-DD).
    Game resets every day at 05:00 AM:
    - 00:00 - 04:59 AM -> Belongs to previous day's cycle (yesterday)
    - 05:00 AM onwards -> Belongs to current day's cycle
    """
    from datetime import timedelta
    now = datetime.now()
    if now.hour < 5:
        game_day = now - timedelta(days=1)
    else:
        game_day = now
    return game_day.strftime("%Y-%m-%d")


def is_daily_completed_today():
    """Checks if tower was already completed for current game cycle (5:00 AM reset)."""
    game_date = get_game_date()
    if DAILY_RECORD_FILE.exists():
        content = DAILY_RECORD_FILE.read_text(encoding="utf-8").strip()
        if content == game_date:
            return True
    return False


def mark_daily_completed_today():
    """Saves current game cycle date so bot won't repeat until next 5:00 AM."""
    game_date = get_game_date()
    DAILY_RECORD_FILE.write_text(game_date, encoding="utf-8")
    print(f"\n[DAILY] Marked Tower run as COMPLETED for game cycle: {game_date} (Resets at 5:00 AM).\n")


# ============================================================
# MAIN TOWER RUNNER
# ============================================================

def run_tower_bot(max_floors=40, force=False):
    game_cycle = get_game_date()
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print()
    print("=" * 60)
    print("      MONSTER SAGA - BATTLE TOWER BOT (บอททาวเวอร์)")
    print("=" * 60)
    print(f"Device:            {DEVICE}")
    print(f"Current Time:      {now_str}")
    print(f"Game Cycle Date:   {game_cycle} (เกมรีเซ็ตทุก 05:00 น.)")
    print("Mode:              ทาวเวอร์ต่อสู้ (ไต่หอคอย 80 ชั้น / วันละ 1 รอบ)")
    print("=" * 60)
    print()

    # Check daily limit
    if not force and is_daily_completed_today():
        print(f"[DAILY] หอคอยของรอบวันนี้ ({game_cycle}) บอทเล่นเสร็จไปแล้ว!")
        print("[DAILY] เกมจะรีเซ็ตรอบใหม่เวลา 05:00 น.")
        print("[DAILY] (หากต้องการบังคับรันซ้ำ ให้ลบไฟล์ 'tower_daily_done.txt' หรือใส่ force=True)")
        return

    if not ensure_device_connected():
        print("ERROR: Device not connected!")
        return

    floors_cleared = 0
    consecutive_unknown = 0

    while floors_cleared < max_floors:
        print()
        print("-" * 50)
        print(f"Floor Step #{floors_cleared + 1} (Cleared so far: {floors_cleared})")
        print("-" * 50)

        img = screenshot()

        # Auto-recovery if currently sitting on Victory screen
        if is_victory_screen(img):
            print("[RECOVERY] Sitting on Victory Screen -> Tapping 'ต่อไป' (800, 630)...")
            tap(VICTORY_NEXT[0], VICTORY_NEXT[1])
            time.sleep(3.0)
            continue

        # Auto-recovery if popup 'เลือกคู่แข่ง' is currently open
        if is_select_opponent_open(img):
            print("[RECOVERY] Sitting on 'เลือกคู่แข่ง' popup -> Proceeding to battle...")
            success = do_battle()
            if not success:
                print("[TOWER] Opponent battle encountered issue.")
                break
            floors_cleared += 1
            time.sleep(2.0)
            continue

        if not is_in_tower_lobby(img):
            print("Waiting for Tower Lobby...")
            time.sleep(2.0)
            consecutive_unknown += 1
            if consecutive_unknown >= 8:
                print("Lobby not detected for 16s. Checking if completed Floor 80!")
                break
            continue

        consecutive_unknown = 0
        target_type = detect_floor_type(img)
        print(f"[DETECT] Floor Target Type: >>> {target_type} <<<")

        if target_type == "TRANSITION":
            print("Floor target still transitioning/moving. Waiting 1.5s...")
            time.sleep(1.5)
            continue

        # Check if already reached Floor 80 (only after elevator/floor transition is settled)
        if is_at_floor_80(img):
            print("\n[TOWER] Floor 80 reached! Tower climb 100% completed.")
            if target_type == "CHEST":
                print("[TOWER] Collecting final Floor 80 chest...")
                do_collect_chest()
                floors_cleared += 1
            break
        elif target_type == "BUFF":
            do_buy_buff()
            floors_cleared += 1
        elif target_type == "CHEST":
            at_80 = is_at_floor_80(img)
            do_collect_chest()
            floors_cleared += 1

            # เมื่อเก็บกล่องที่ชั้น 80 เสร็จแล้ว ให้หยุดทำงานทันที (ไม่วนซ้ำ)
            if at_80:
                print("\n[TOWER] Finished Floor 80! Final chest collected. Stopping script.\n")
                break
        else: # OPPONENT
            success = do_battle()
            if not success:
                print("[TOWER] Opponent battle encountered issue.")
                break
            floors_cleared += 1

        time.sleep(2.0)

    # Mark completed for today once finished
    if floors_cleared > 0:
        mark_daily_completed_today()

    print()
    print("=" * 60)
    print(f"TOWER CLIMB COMPLETED! Total floor steps cleared: {floors_cleared}")
    print("=" * 60)
    print()


if __name__ == "__main__":
    run_tower_bot(max_floors=40)
