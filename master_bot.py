#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
MonsterBot Master Orchestrator (Full-Game Autonomous System)
Coordinates daily claims, limited-entry tower climb, and champion arena.
"""

import sys
import os
import json
import time
import argparse
from datetime import datetime

# UTF-8 stdout configuration for Windows PowerShell
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace", line_buffering=True)

from core.adb_client import AdbClient
from core.vision import Vision
from core.navigator import Navigator
from core.recovery import Recovery
from core.notifier import Notifier

from tasks.task_daily_claim import DailyClaimTask
from tasks.task_tower_hard import TowerHardTask
from tasks.task_champion import ChampionTask


class MasterBot:
    """Central Controller for Autonomous Game Automation."""

    def __init__(self, config_path: str = "config/config.json"):
        self.base_dir = os.path.dirname(os.path.abspath(__file__))
        self.config_file = os.path.join(self.base_dir, config_path)
        self.config = self._load_config()

        # Core Components
        emu_cfg = self.config.get("emulator", {})
        self.adb = AdbClient(
            adb_path=emu_cfg.get("adb_path", r"C:\Program Files\Netease\MuMuPlayer\nx_main\adb.exe"),
            device_serial=emu_cfg.get("device", "127.0.0.1:5559")
        )
        self.vision = Vision(templates_dir=os.path.join(self.base_dir, "templates"))
        self.navigator = Navigator(self.adb, self.vision, self.config)
        self.recovery = Recovery(self.adb, self.vision, self.config)
        self.notifier = Notifier(self.config)

        # Registered Tasks (Ordered by Priority)
        state_path = os.path.join(self.base_dir, "data", "daily_state.json")
        self.tasks = [
            DailyClaimTask(self.adb, state_file=state_path),
            TowerHardTask(max_floors=100),
            ChampionTask(run_mode="continuous"),
        ]

    def _load_config(self) -> dict:
        if os.path.exists(self.config_file):
            with open(self.config_file, "r", encoding="utf-8") as f:
                return json.load(f)
        return {}

    def test_navigation(self):
        """Diagnostic routine to test ADB, screencap, and screen detection."""
        print("\n" + "=" * 60)
        print("MONSTERBOT SYSTEM DIAGNOSTICS")
        print("=" * 60)
        print(f"Target Device: {self.adb.device_serial}")
        print("Capturing frame...")
        
        try:
            img = self.adb.screencap()
            h, w = img.shape[:2]
            print(f"Frame Captured: {w}x{h} pixels (RGB/BGR)")
            
            screen_name = self.navigator.identify_screen(img)
            print(f"Detected Game Screen: [{screen_name}]")
            
            auto_on = self.vision.is_auto_on(img)
            auto_off = self.vision.is_auto_off(img)
            print(f"AUTO Status: {'ON (Yellow)' if auto_on else 'OFF (Blue)' if auto_off else 'Not Detected'}")
            
            is_lobby = self.navigator.is_in_lobby(img)
            print(f"Is In Main Lobby: {is_lobby}")
            print("=" * 60 + "\n")
        except Exception as e:
            print(f"Diagnostic Error: {e}")

    def run_single_task(self, task_name: str):
        """Run a specific task by name."""
        matched = [t for t in self.tasks if task_name.lower() in t.name.lower()]
        if not matched:
            print(f"[Master] ไม่พบภารกิจชื่อ '{task_name}'")
            return
        
        task = matched[0]
        print(f"[Master] สั่งรันภารกิจเฉพาะกิจ: {task.name}")
        self.navigator.return_to_lobby()
        task.execute()
        self.navigator.return_to_lobby()

    def run_autonomous_loop(self):
        """Main 24/7 Autonomous Game Engine Loop."""
        print("\n" + "=" * 65)
        print("  STARTING MONSTERBOT MASTER AUTONOMOUS ENGINE (24/7 LOOP)")
        print("=" * 65 + "\n")
        self.notifier.send("MonsterBot Online", "บอทเริ่มทำงานในโหมด Full-Game Autonomous เรียบร้อยแล้ว")

        idle_seconds = self.config.get("routine", {}).get("idle_sleep_seconds", 1800)

        while True:
            try:
                # 1. Health check: Is game running?
                if not self.recovery.is_game_alive():
                    print("[Master] แอปเกมไม่ได้เปิดอยู่ กำลังสั่งเปิดใหม่อัตโนมัติ...")
                    self.recovery.restart_game()
                    self.navigator.return_to_lobby()

                # 2. Iterate through tasks by priority
                action_executed = False
                for task in sorted(self.tasks, key=lambda t: t.priority):
                    if task.can_run():
                        print(f"\n>>> [Master] กำลังเริ่มขั้นตอน: {task.name} (ลำดับความสำคัญ {task.priority}) <<<")
                        
                        # Ensure we are in Lobby before starting navigation
                        self.navigator.return_to_lobby()

                        # Execute the task
                        success = task.execute()

                        # Return to safety
                        self.navigator.return_to_lobby()
                        action_executed = True
                        break  # Re-evaluate tasks from priority 1

                # 3. If no tasks currently require execution, enter Idle Sleep
                if not action_executed:
                    print(f"\n[Master] ภารกิจจำกัดรอบเสร็จสิ้นทั้งหมดแล้ว เข้าสู่โหมดพัก {idle_seconds // 60} นาที...")
                    time.sleep(idle_seconds)

            except KeyboardInterrupt:
                print("\n\n" + "=" * 60)
                print("MASTER BOT STOPPED BY USER (CTRL+C)")
                print("=" * 60 + "\n")
                break
            except Exception as e:
                print(f"\n[Master Error] เกิดข้อผิดพลาดในลูปหลัก: {e}")
                time.sleep(5)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="MonsterBot Master Orchestrator")
    parser.add_argument("--test-nav", action="store_true", help="Test screen detection and ADB frame capture")
    parser.add_argument("--task", type=str, help="Run a specific task (e.g. daily, tower, champ)")
    args = parser.parse_args()

    bot = MasterBot()

    if args.test_nav:
        bot.test_navigation()
    elif args.task:
        bot.run_single_task(args.task)
    else:
        bot.run_autonomous_loop()
