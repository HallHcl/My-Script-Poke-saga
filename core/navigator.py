import time
from typing import Optional
from core.adb_client import AdbClient
from core.vision import Vision


class Navigator:
    """Universal Screen State Recognition and Navigation Graph Router."""

    def __init__(self, adb: AdbClient, vision: Vision, config: dict):
        self.adb = adb
        self.vision = vision
        self.config = config

    def identify_screen(self, image=None) -> str:
        """Identify which game screen is currently active."""
        if image is None:
            image = self.adb.screencap()

        # 1. Check Lobby (Match button present)
        match_thresh = self.config.get("thresholds", {}).get("match", 0.90)
        if self.vision.match(image, "match_button.png", threshold=match_thresh):
            return "LOBBY"

        # 2. Check Victory / Result Screen (Return button present)
        btn_thresh = self.config.get("thresholds", {}).get("button_type", 0.88)
        if self.vision.match(image, "return_button.png", threshold=btn_thresh):
            return "SUMMARY"

        # 3. Check Battle (Auto button present)
        if self.vision.is_auto_on(image) or self.vision.is_auto_off(image):
            return "BATTLE"

        # 4. Check Tower Floor Badges
        if self.vision.match(image, "badge_floor_80.png", threshold=0.85) or \
           self.vision.match(image, "badge_normal_80.png", threshold=0.85):
            return "TOWER"

        return "UNKNOWN"

    def is_in_lobby(self, image=None) -> bool:
        """Return True if currently on the main Lobby screen."""
        return self.identify_screen(image) == "LOBBY"

    def return_to_lobby(self, max_attempts: int = 8) -> bool:
        """
        Universal Escape Function: Continuously dismisses popups / presses back
        until the Lobby screen is confirmed.
        """
        for attempt in range(1, max_attempts + 1):
            img = self.adb.screencap()
            screen = self.identify_screen(img)

            if screen == "LOBBY":
                print(f"[Navigator] อยู่ที่หน้า Lobby เรียบร้อยแล้ว (ตรวจพบในรอบที่ {attempt})")
                return True

            print(f"[Navigator] กำลังนำทางกลับสู่ Lobby... (สถานะปัจจุบัน: {screen}, รอบที่ {attempt}/{max_attempts})")

            # Check for result return button
            ret_match = self.vision.match(img, "return_button.png", threshold=0.85)
            if ret_match:
                self.adb.tap(ret_match[0], ret_match[1])
                time.sleep(1.5)
                continue

            # Check for top-right close button (X)
            self.adb.tap(1230, 45)
            time.sleep(0.8)

            # Android Back Key as safety net
            self.adb.key_back()
            time.sleep(1.2)

        # Final verification
        final_img = self.adb.screencap()
        return self.is_in_lobby(final_img)

    def navigate_to(self, target: str) -> bool:
        """Navigate from current location to target game section."""
        target = target.upper()

        # Step 1: Always reset to Lobby first for safety
        if not self.is_in_lobby():
            if not self.return_to_lobby():
                print(f"[Navigator] ล้มเหลวในการกลับสู่ Lobby ไม่สามารถเดินทางไป {target} ได้")
                return False

        # Step 2: Route from Lobby to target
        coords = self.config.get("coordinates", {})
        if target in ["CHAMPION", "CHAMP"]:
            print("[Navigator] เข้าสู่โหมด Champion จาก Lobby")
            return True

        elif target in ["TOWER", "TOWER_HARD"]:
            print("[Navigator] กำลังเดินทางไปยังหอคอย...")
            # Tap Tower / Adventure button
            tower_btn = coords.get("lobby", {}).get("tower_button", [150, 185])
            self.adb.tap(tower_btn[0], tower_btn[1])
            time.sleep(2.0)
            return True

        return False
