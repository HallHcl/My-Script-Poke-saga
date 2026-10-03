import os
import json
import time
from datetime import datetime
from tasks.base_task import BaseTask
from core.adb_client import AdbClient


class DailyClaimTask(BaseTask):
    """Task for claiming daily mailbox rewards, sign-ins, and freebies."""

    def __init__(self, adb: AdbClient, state_file: str = "data/daily_state.json"):
        super().__init__(name="Daily Claims", priority=1, target_screen="LOBBY")
        self.adb = adb
        self.state_file = state_file

    def _get_today_str(self) -> str:
        return datetime.now().strftime("%Y-%m-%d")

    def can_run(self) -> bool:
        """Check if daily claims have already been completed today."""
        if not os.path.exists(self.state_file):
            return True
        try:
            with open(self.state_file, "r", encoding="utf-8") as f:
                data = json.load(f)
            return self._get_today_str() not in data.get("completed_tasks", [])
        except Exception:
            return True

    def execute(self) -> bool:
        print(f"\n{'='*50}\n[Task: {self.name}] กำลังตรวจสอบและรับของรางวัลประจำวัน...\n{'='*50}")

        # 1. Mailbox Claim
        print("[Daily Claims] กำลังเปิดกล่องจดหมาย...")
        self.adb.tap(1210, 45) # Top-right mailbox icon
        time.sleep(2.0)

        # Tap 'Claim All' / รับทั้งหมด
        print("[Daily Claims] กดรับจดหมายทั้งหมด...")
        self.adb.tap(800, 640)
        time.sleep(1.5)

        # Dismiss reward dialog
        self.adb.tap(640, 500)
        time.sleep(1.0)

        # Close mailbox window
        self.adb.tap(1230, 45)
        time.sleep(1.5)

        # 2. Record completion in state
        try:
            today = self._get_today_str()
            data = {"completed_tasks": [], "last_reset_date": today}
            if os.path.exists(self.state_file):
                with open(self.state_file, "r", encoding="utf-8") as f:
                    data = json.load(f)

            if today not in data.get("completed_tasks", []):
                data.setdefault("completed_tasks", []).append(today)

            with open(self.state_file, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"[Daily Claims] ไม่สามารถบันทึกสถานะ: {e}")

        self.on_complete()
        return True
