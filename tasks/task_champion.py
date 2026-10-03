import os
import sys
import subprocess
from tasks.base_task import BaseTask


class ChampionTask(BaseTask):
    """Task for Champion Arena matchmaking and wave battle loop."""

    def __init__(self, run_mode: str = "continuous", script_name: str = "champ_bot_season2.py"):
        super().__init__(name="Champion Arena", priority=4, target_screen="CHAMPION")
        self.run_mode = run_mode
        self.script_name = script_name

    def can_run(self) -> bool:
        # Champion is typically available to farm indefinitely
        return True

    def execute(self) -> bool:
        print(f"\n{'='*50}\n[Task: {self.name}] กำลังเริ่มฟาร์มศึก Champion ({self.script_name})...\n{'='*50}")
        script_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), self.script_name)

        try:
            # Run champ_bot
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
