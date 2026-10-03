import time
from core.adb_client import AdbClient
from core.vision import Vision


class Recovery:
    """Watchdog and Autonomous Crash Recovery System."""

    def __init__(self, adb: AdbClient, vision: Vision, config: dict):
        self.adb = adb
        self.vision = vision
        self.config = config
        self.package_name = self.config.get("emulator", {}).get("package_name", "com.monster.saga")

    def is_game_alive(self) -> bool:
        """Check if the game process is running on the device."""
        return self.adb.is_package_running(self.package_name)

    def restart_game(self, wait_seconds: int = 25):
        """Force restart the game and wait for the title screen to load."""
        print(f"[Recovery] ตรวจพบเกมขัดข้อง กำลังรีสตาร์ทแอป {self.package_name}...")
        self.adb.restart_app(self.package_name)
        print(f"[Recovery] รอโหลดเข้าเกม {wait_seconds} วินาที...")
        time.sleep(wait_seconds)

        # Clear starting daily popups / announcements
        self.dismiss_popups(cycles=4)

    def dismiss_popups(self, cycles: int = 3):
        """Dismiss common promotional and announcement dialogs."""
        for _ in range(cycles):
            # Top-right close button
            self.adb.tap(1230, 45, jitter=True)
            time.sleep(0.7)
            # Center confirm / OK button
            self.adb.tap(640, 500, jitter=True)
            time.sleep(0.7)
