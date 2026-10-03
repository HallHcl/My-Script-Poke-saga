import sys
import cv2  # type: ignore
import numpy as np
import subprocess
import time
import os
from datetime import datetime, timedelta
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
TPL_FLOOR_80 = BASE_DIR / "templates" / "badge_floor_80.png"
TPL_DIGIT_8 = BASE_DIR / "templates" / "digit_8.png"
TPL_DIGIT_0 = BASE_DIR / "templates" / "digit_0.png"

# ============================================================
# VERIFIED COORDINATES (1280x720 Native Resolution - Hard Mode)
# ============================================================

# Mode Tab
TAB_CHALLENGE = (150, 185)       # "ท้าทาย" (Hard Mode) top-left tab

# 1. Opponent Battle
OPPONENT = (707, 520)           # Click enemy standing in center
CHALLENGE_BTN = (638, 410)      # "ท้าทาย" Gold Button in personal battle popup

# In-Battle Controls
AUTO_TOWER = (52, 255)          # "ต่อสู้ออโต้" button in Tower battle
VICTORY_NEXT = (800, 630)       # "ต่อไป" button on victory screen (must tap)

# 2. Buff Station
BUFF_EMBLEM = (706, 586)        # Pokeball emblem on buff platform
BUFF_CARDS_X = [304, 642, 980]  # Left, Middle, Right card centers
BUFF_BUY_Y = 531                # "ซื้อ!!!" button Y coordinate
BUFF_CLOSE_X = (1230, 43)       # Close button (cyan X top-right)
BUFF_CONFIRM_OK = (717, 411)    # "ตกลง" button on warning popup ("ยังมีbuffไม่ได้ซื้อ จะปิดไหม")

# 3. Treasure Chest
CHEST_TARGET = (707, 600)       # Click golden chest in center
CHEST_DISMISS = (500, 460)      # Tap reward screen to dismiss
CHEST_LEAVE = (430, 575)        # "ทิ้งไว้" button to avoid spending diamonds (Center verified)


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


def screenshot(save=False, prefix="tower_hard"):
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
    """
    Checks if currently in Tower lobby screen:
    - Yellow 'X' close button at top-right (15:60, 1220:1265)
    - Cyan title 'ศึกทาวเวอร์' / 'โหมดท้าทายศึกทาวเวอร์' at top-left (15:55, 15:200)
    This strictly excludes Battle Arena, Victory screens, and popups.
    """
    if img is None or img.shape[:2] != (720, 1280):
        return False

    crop_x = img[15:60, 1220:1265]
    hsv_x = cv2.cvtColor(crop_x, cv2.COLOR_BGR2HSV)
    yellow_x = np.count_nonzero(cv2.inRange(hsv_x, np.array([15, 100, 150]), np.array([35, 255, 255])))

    crop_title = img[15:55, 15:200]
    hsv_title = cv2.cvtColor(crop_title, cv2.COLOR_BGR2HSV)
    cyan_title = np.count_nonzero(cv2.inRange(hsv_title, np.array([85, 100, 150]), np.array([105, 255, 255])))

    return yellow_x > 250 and cyan_title > 2000


def is_tower_auto_off(img):
    """Checks if 'ต่อสู้ออโต้' button is visible in blue/cyan (meaning AUTO is currently OFF)."""
    if img is None:
        return False
    crop = img[210:300, 10:95]
    b, g, r = cv2.split(crop)
    cyan = (b > 180) & (g > 180) & (r < 100)
    return np.count_nonzero(cyan) > 200


def is_victory_screen(img):
    """
    Checks if victory screen is visible:
    - Yellow 'ต่อไป' button at (730:860, 600:660)
    - Yellow 'กลับ' button at (430:560, 600:660)
    - Golden 'ชนะการต่อสู้' victory banner at (400:880, 80:200)
    """
    if img is None or img.shape[:2] != (720, 1280):
        return False
    hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
    btn_next = cv2.inRange(hsv[600:660, 730:860], np.array([12, 100, 150]), np.array([28, 255, 255]))
    btn_back = cv2.inRange(hsv[600:660, 430:560], np.array([12, 100, 150]), np.array([28, 255, 255]))
    banner_mask = cv2.inRange(hsv[80:200, 400:880], np.array([12, 120, 180]), np.array([25, 255, 255]))
    return np.count_nonzero(btn_next) > 2000 and np.count_nonzero(btn_back) > 2000 and np.count_nonzero(banner_mask) > 3000


def is_in_battle_arena(img):
    """Checks if currently in battle arena (Speed X3 button visible and lobby close button absent)."""
    if img is None:
        return False
    crop_x3 = img[135:195, 10:70]
    hsv_x3 = cv2.cvtColor(crop_x3, cv2.COLOR_BGR2HSV)
    cyan_x3 = np.count_nonzero(cv2.inRange(hsv_x3, np.array([85, 100, 150]), np.array([105, 255, 255])))
    crop_close = img[15:60, 1220:1265]
    hsv_close = cv2.cvtColor(crop_close, cv2.COLOR_BGR2HSV)
    yellow_close = np.count_nonzero(cv2.inRange(hsv_close, np.array([15, 100, 150]), np.array([35, 255, 255])))
    return cyan_x3 > 300 and yellow_close < 100


def is_team_battle_popup(img):
    """Checks if 'การต่อสู้ทีม' (Team Battle) modal is open."""
    if img is None or is_in_tower_lobby(img):
        return False
    hsv_title = cv2.cvtColor(img[20:75, 400:650], cv2.COLOR_BGR2HSV)
    cyan_title = np.count_nonzero(cv2.inRange(hsv_title, np.array([85, 100, 150]), np.array([105, 255, 255])))
    if cyan_title < 1800:
        return False
    hsv_badge = cv2.cvtColor(img[160:300, 80:200], cv2.COLOR_BGR2HSV)
    gold_badge = np.count_nonzero(cv2.inRange(hsv_badge, np.array([15, 100, 150]), np.array([30, 255, 255])))
    return gold_badge > 400


def is_personal_battle_popup(img):
    """Checks if 'การต่อสู้ส่วนบุคคล' (Personal Battle) modal is open."""
    if img is None or is_in_tower_lobby(img):
        return False
    hsv_title = cv2.cvtColor(img[20:75, 400:650], cv2.COLOR_BGR2HSV)
    cyan_title = np.count_nonzero(cv2.inRange(hsv_title, np.array([85, 100, 150]), np.array([105, 255, 255])))
    if cyan_title < 1800:
        return False
    hsv_btn = cv2.cvtColor(img[380:440, 580:700], cv2.COLOR_BGR2HSV)
    gold_btn = np.count_nonzero(cv2.inRange(hsv_btn, np.array([15, 60, 150]), np.array([30, 255, 255])))
    return not is_team_battle_popup(img) and gold_btn > 200


def is_at_floor_80(img):
    """
    Checks if currently on Floor 80:
    1. Must be in Tower Lobby
    2. Isolates yellow text from floor badge crop (365:405, 80:150)
    3. Verifies presence of digit '8' AND digit '0' via template matching (> 0.88 each)
       This completely eliminates false positives from Floor 68, 69, 70, etc.
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
    if img is None:
        return "UNKNOWN"

    # 1. Check if Opponent Head is present right below arrow
    # (Opponents have high intensity/head pixels, background is dark space < 35)
    head_crop = img[480:540, 675:740]
    gray_head = cv2.cvtColor(head_crop, cv2.COLOR_BGR2GRAY)
    if gray_head.mean() > 40:
        return "OPPONENT"

    # 2. Distinguish between BUFF and CHEST
    crop_center = img[550:640, 660:750]
    b, g, r = cv2.split(crop_center)
    cyan_count = np.count_nonzero((b > 180) & (g > 180) & (r < 150))
    gold_count = np.count_nonzero((r > 180) & (g > 150) & (b < 100))

    if cyan_count > 250:
        return "BUFF"
    elif gold_count > 200:
        return "CHEST"

    return "TRANSITION"


def is_challenge_tab_active(img):
    if img is None:
        return False
    crop_tab2 = img[150:220, 115:185]
    b, g, r = cv2.split(crop_tab2)
    gold = (r > 200) & (g > 140) & (b < 100)
    return np.count_nonzero(gold) > 200


def ensure_challenge_tab():
    """Ensures Hard/Challenge tab is selected on tower lobby screen."""
    img = screenshot()
    if img is None or not is_in_tower_lobby(img):
        return
    if not is_challenge_tab_active(img):
        print("[MODE] Tapping Hard / Challenge Mode Tab...")
        tap(TAB_CHALLENGE[0], TAB_CHALLENGE[1])
        time.sleep(2.0)


# ============================================================
# SMART BUFF PURCHASING SYSTEM
# ============================================================

def is_buff_available(img, card_x):
    """Checks if the card button is 'ซื้อ!!!' (Yellow glowing button)."""
    btn_crop = img[500:560, card_x - 70:card_x + 70]
    hsv = cv2.cvtColor(btn_crop, cv2.COLOR_BGR2HSV)
    yellow_mask = cv2.inRange(hsv, np.array([20, 100, 180]), np.array([35, 255, 255]))
    return np.count_nonzero(yellow_mask) > 150


def is_heal_buff(img, card_x):
    """Checks if the buff card icon is predominantly Green (Heal/ฟื้นฟู)."""
    # Icon box is y: 240 to 340, x: card_x - 45 to card_x + 45
    icon_crop = img[240:340, card_x - 45:card_x + 45]
    hsv = cv2.cvtColor(icon_crop, cv2.COLOR_BGR2HSV)
    # Green Hue [35, 85]
    green_mask = cv2.inRange(hsv, np.array([35, 80, 80]), np.array([85, 255, 255]))
    # Genuine heal buff has green icon body (> 700 pixels), while other buffs only have a tiny up-arrow (~200 pixels)
    return np.count_nonzero(green_mask) > 700


def is_confirm_warning_visible(img):
    """Checks if popup 'ยังมีbuffไม่ได้ซื้อ จะปิดไหม' is visible."""
    # Text popup box has dark blue center at (640, 360)
    crop = img[350:450, 600:750] # "ตกลง" button region
    hsv = cv2.cvtColor(crop, cv2.COLOR_BGR2HSV)
    cyan_mask = cv2.inRange(hsv, np.array([85, 100, 100]), np.array([105, 255, 255]))
    return np.count_nonzero(cyan_mask) > 200


def do_buy_buff():
    """
    Opens buff window, prioritizes:
      1. Non-Heal buffs (Atk, Def, Spd, Crit, etc.)
      2. Heal buffs (Green) LAST
    Buys as many buffs as possible until coins run out (< 15) or no more buffs left.
    """
    print("[TOWER BUFF] 1. Opening buff platform...")
    tap(BUFF_EMBLEM[0], BUFF_EMBLEM[1])
    time.sleep(2.0)

    # Multi-purchase loop
    bought_count = 0
    max_purchases = 3

    for attempt in range(max_purchases):
        img = screenshot()
        if img is None:
            break

        # Scan all 3 cards
        card_candidates = []
        for idx, cx in enumerate(BUFF_CARDS_X):
            available = is_buff_available(img, cx)
            if available:
                is_heal = is_heal_buff(img, cx)
                # Priority: 0 for normal buffs, 1 for heal buffs (last)
                priority = 1 if is_heal else 0
                card_candidates.append({
                    "card_index": idx + 1,
                    "x": cx,
                    "is_heal": is_heal,
                    "priority": priority
                })

        if not card_candidates:
            print("[TOWER BUFF] No available buffs left to buy.")
            break

        # Sort: Non-heal first (priority 0), Heal last (priority 1)
        card_candidates.sort(key=lambda c: c["priority"])
        target = card_candidates[0]
        type_str = "Heal (สีเขียว)" if target["is_heal"] else "General/Atk/Def"
        print(f"[TOWER BUFF] Buying Card #{target['card_index']} ({type_str}) at ({target['x']}, {BUFF_BUY_Y})...")

        tap(target["x"], BUFF_BUY_Y)
        time.sleep(1.8)

        # Verify if purchase succeeded (button turned into 'ซื้อแล้ว')
        img_after = screenshot()
        if not is_buff_available(img_after, target["x"]):
            bought_count += 1
            print(f"[TOWER BUFF] Successfully bought Buff #{bought_count}!")
        else:
            print("[TOWER BUFF] Coins insufficient (< 15). Stopping further buff purchases.")
            break

    # Close popup if not already closed automatically
    time.sleep(1.0)
    closed_auto = False
    for _ in range(3):
        img_check = screenshot()
        if is_in_tower_lobby(img_check):
            closed_auto = True
            break
        time.sleep(0.8)

    if closed_auto:
        print("[TOWER BUFF] Buff window closed automatically! Back in Tower Lobby.")
    else:
        # Window is still open (e.g. bought < 3 buffs because coins ran out)
        print("[TOWER BUFF] Closing buff window (buffs remaining)...")
        tap(BUFF_CLOSE_X[0], BUFF_CLOSE_X[1])
        time.sleep(1.5)

        # Check if warning popup appears ("ยังมีbuffไม่ได้ซื้อ จะปิดไหม")
        img_warning = screenshot()
        if is_confirm_warning_visible(img_warning):
            print("[TOWER BUFF] Confirming warning popup ('ตกลง')...")
            tap(BUFF_CONFIRM_OK[0], BUFF_CONFIRM_OK[1])
            time.sleep(1.8)

    print(f"[TOWER BUFF] Buff station completed. Total buffs purchased: {bought_count}\n")
    return True


# ============================================================
# ACTIONS
# ============================================================

def tap_challenge_button():
    """Taps 'ท้าทาย' button whether in personal battle or team battle, and handles formation screen if opened."""
    time.sleep(1.5)
    for attempt in range(4):
        img = screenshot()
        if img is None:
            break

        # 1. Check if formation screen opened ("บันทึก" button present at 1175, 484)
        hsv_save = cv2.cvtColor(img[450:515, 1090:1260], cv2.COLOR_BGR2HSV)
        gold_save = cv2.inRange(hsv_save, np.array([15, 120, 150]), np.array([28, 255, 255]))
        if np.count_nonzero(gold_save) > 500:
            print("    [FORMATION] 'บันทึก' button detected! Tapping (1175, 484)...")
            tap(1175, 484)
            time.sleep(2.0)
            continue

        # 2. Check if Team Battle popup ("ท้าทาย" button at 638, 495)
        if is_team_battle_popup(img):
            print("    [CHALLENGE] Team battle detected! Selecting opponent and tapping 'ท้าทาย' (638, 495)...")
            tap(660, 520)
            time.sleep(0.5)
            tap(638, 495)
            return True

        # 3. Check if Personal Battle popup ("ท้าทาย" button at 638, 410)
        if is_personal_battle_popup(img):
            print("    [CHALLENGE] Personal battle detected! Tapping 'ท้าทาย' (638, 410)...")
            tap(638, 410)
            return True

        time.sleep(1.0)

    # Fallback
    print("    [CHALLENGE] Tapping challenge fallback (638, 410) & (638, 495)...")
    tap(638, 410)
    time.sleep(0.5)
    tap(638, 495)
    return True


def do_battle_monitor(start_wait=None, max_wait=600):
    """Monitors ongoing battle (single or multi-waves) until returning to Tower Lobby."""
    if start_wait is None:
        start_wait = time.time()
    last_auto_tap = 0
    waves_cleared = 0

    while time.time() - start_wait < max_wait:
        time.sleep(2.0)
        img = screenshot()

        # Check if victory screen appeared (Wave or Final)
        if is_victory_screen(img):
            waves_cleared += 1
            print(f"[TOWER BATTLE] Victory screen #{waves_cleared} detected! Tapping 'ต่อไป' (800, 630)...")
            tap(VICTORY_NEXT[0], VICTORY_NEXT[1])
            time.sleep(3.0)
            # Re-check if victory screen is still up (tap again if necessary)
            for _ in range(3):
                img_v = screenshot()
                if is_victory_screen(img_v):
                    print("    [VICTORY] Retapping 'ต่อไป' (800, 630)...")
                    tap(VICTORY_NEXT[0], VICTORY_NEXT[1])
                    time.sleep(1.5)
                else:
                    break
            continue

        # Check if Team battle popup reopened (between waves of 3v3 team battle)
        if is_team_battle_popup(img):
            print("    [TEAM BATTLE] Next opponent ready! Tapping 'ท้าทาย' (638, 495)...")
            tap(660, 520)
            time.sleep(0.5)
            tap(638, 495)
            time.sleep(3.0)
            continue

        # Check if returned to Tower lobby screen
        # Must have cleared at least 1 wave or elapsed > 15s to prevent premature exit
        if (waves_cleared > 0 or (time.time() - start_wait > 15.0)) and is_in_tower_lobby(img):
            print(f"[TOWER BATTLE] Back in Tower Lobby! (Waves cleared: {waves_cleared})")
            time.sleep(2.0)
            return True

        # Check if AUTO is OFF in battle -> Tap to turn ON
        if is_tower_auto_off(img):
            if time.time() - last_auto_tap > 4.0:
                print("    [AUTO OFF] Tapping AUTO (52, 255)...")
                tap(AUTO_TOWER[0], AUTO_TOWER[1])
                last_auto_tap = time.time()

    print("[TOWER BATTLE] Warning: Battle timed out.")
    return False


def do_battle():
    """
    Handles opponent selection in Hard mode (Gold Challenge Button),
    enters battle, enables auto, and handles multiple victory waves
    until successfully returning to Tower Lobby.
    """
    print("[TOWER BATTLE] 1. Tapping opponent...")
    tap(OPPONENT[0], OPPONENT[1])

    print("[TOWER BATTLE] 2. Tapping 'ท้าทาย' button...")
    tap_challenge_button()

    print("[TOWER BATTLE] 3. Waiting to enter battle arena...")
    time.sleep(3.0)
    entered_battle = False
    for _ in range(12):
        img_check = screenshot()
        if not is_in_tower_lobby(img_check):
            entered_battle = True
            break
        time.sleep(1.0)

    if not entered_battle:
        print("[TOWER BATTLE] Still in lobby, retrying challenge button tap...")
        tap_challenge_button()
        time.sleep(3.0)

    print("[TOWER BATTLE] 4. Monitoring battle (supporting multi-waves)...")
    return do_battle_monitor()


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
# MAIN TOWER HARD RUNNER
# ============================================================

def run_tower_hard_bot(max_floors=100):
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print()
    print("=" * 65)
    print("   MONSTER SAGA - BATTLE TOWER BOT (โหมด HARD / ท้าทาย)")
    print("=" * 65)
    print(f"Device:            {DEVICE}")
    print(f"Current Time:      {now_str}")
    print("Mode:              โหมดท้าทาย (Hard Mode - ไต่หอคอย 80 ชั้น)")
    print("Buff Strategy:     ซื้อทุกบัฟจนเหรียญหมด (ฮีลสีเขียวซื้อหลังสุด)")
    print("=" * 65)
    print()

    if not ensure_device_connected():
        print("ERROR: Device not connected!")
        return

    # Ensure we are on Hard/Challenge Tab
    ensure_challenge_tab()

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

        # Auto-recovery if currently in Battle Arena
        if is_in_battle_arena(img):
            print("[RECOVERY] Battle Arena detected! Continuing monitor...")
            success = do_battle_monitor(start_wait=time.time())
            if not success:
                print("[TOWER HARD] Battle encountered issue or timeout.")
                break
            floors_cleared += 1
            continue

        # Auto-recovery if currently in Team battle popup
        if is_team_battle_popup(img):
            print("[RECOVERY] Team battle popup detected! Starting challenge...")
            tap(660, 520)
            time.sleep(0.5)
            tap(638, 495)
            success = do_battle_monitor(start_wait=time.time())
            if not success:
                print("[TOWER HARD] Battle encountered issue or timeout.")
                break
            floors_cleared += 1
            continue

        # Auto-recovery if currently in Personal battle popup
        if is_personal_battle_popup(img):
            print("[RECOVERY] Personal battle popup detected! Tapping 'ท้าทาย' (638, 410)...")
            tap(638, 410)
            success = do_battle_monitor(start_wait=time.time())
            if not success:
                print("[TOWER HARD] Battle encountered issue or timeout.")
                break
            floors_cleared += 1
            continue

        if not is_in_tower_lobby(img):
            print("Waiting for Tower Lobby...")
            time.sleep(2.0)
            consecutive_unknown += 1
            if consecutive_unknown >= 15:
                print("Lobby not detected for 30s. Stopping.")
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
            print("\n[TOWER HARD] Floor 80 reached! Tower climb 100% completed.")
            if target_type == "CHEST":
                print("[TOWER HARD] Collecting final Floor 80 chest...")
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
                print("\n[TOWER HARD] Finished Floor 80! Final chest collected. Stopping script.\n")
                break
        else: # OPPONENT
            success = do_battle()
            if not success:
                print("[TOWER HARD] Opponent battle encountered issue or timeout.")
                break
            floors_cleared += 1

        time.sleep(2.0)

    print()
    print("=" * 65)
    print(f"TOWER HARD CLIMB COMPLETED! Total floor steps cleared: {floors_cleared}")
    print("=" * 65)
    print()


if __name__ == "__main__":
    run_tower_hard_bot(max_floors=100)
