import os
import sys
import subprocess
from tasks.base_task import BaseTask


class TowerHardTask(BaseTask):
    """Task for executing Tower Hard Challenge mode to Floor 80."""

    def __init__(self, max_floors: int = 100):
        super().__init__(name="Tower Hard", priority=2, target_screen="TOWER_HARD")
        self.max_floors = max_floors

    def can_run(self) -> bool:
        # Check if tower was completed today
        return True

    def execute(self) -> bool:
        print(f"\n{'='*50}\n[Task: {self.name}] กำลังเริ่มไต่หอคอยโหมด Hard...\n{'='*50}")
        script_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "tower_hard_bot.py")

        try:
            # Run tower_hard_bot with process isolation
            proc = subprocess.run([sys.executable, script_path], check=False)
            if proc.returncode == 0:
                self.on_complete()
                return True
            else:
                self.on_error(f"Exit code {proc.returncode}")
                return False
        except Exception as e:
            self.on_error(str(e))
            return False
