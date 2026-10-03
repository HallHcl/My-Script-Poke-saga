#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
MonsterBot - Secret Realm Auto Farm & Level Up Bot
===================================================
วงจรการทำงานอัตโนมัติ (Autonomous Secret Realm Farm & Level Up Loop):
1. Phase 1 (ฟาร์มจับโปเกมอน):
   - วนกด "จับอีกครั้ง" (templates/catch_again_button.png หรือพิกัด 752, 559)
   - ดักจับ Popup กระเป๋าเต็ม 120/120 (templates/dialog_ok_button.png หรือพิกัด 647, 419)
   - เมื่อกระเป๋าเต็ม:
     - กด "ตกลง" (647, 419)
     - กด "ปิด" ป๊อปอัปผลการจับ (526, 563)
     - กดปุ่ม "X" ขวาบน (1237, 42) สองครั้งเพื่อกลับสู่หน้า Lobby

2. Phase 2 (รวมเลเวล & เคลียร์กระเป๋า):
   - จาก Lobby: กดปุ่ม "โปเกมอน" ล่างขวา (1125, 665)
   - เลือกโปเกมอนตัวหลักเป้าหมาย (ตัวที่ 5 - W.Kyurem) ที่พิกัด (1100, 280)
   - กดแท็บ "ฝึก" ขวากลางล่าง (1230, 487)
   - ลูปย่อยรวมโปเกมอน (Sub-loop):
     - ตรวจสอบ templates/guardian_pet_text.png
     - หากพบข้อความ "การ์เดียนเพท" -> หยุดรวมทันที! (เพื่อไม่ให้เด้ง Popup เตือน)
     - แตะเลือกโปเกมอน 12 ช่อง (แถวละ 4 ตัว x 3 แถว)
     - กดปุ่มสีทอง "รวม" (1065, 670)
     - หน่วงเวลาและทำซ้ำจนกว่าจะเหลือแต่การ์เดียนเพท
   - กดปุ่ม "X" ขวาบน (1237, 42) สองครั้งเพื่อกลับสู่ Lobby

3. Phase 3 (เดินทางกลับเข้าเขตลับ โซนธรรมดา):
   - จาก Lobby: กดปุ่ม "ฝึก" ขวาบน (1140, 55)
   - กดแท็บ "ผจญภัย" (80, 390)
   - เลื่อนหน้าจอลง (swipe)
   - กดปุ่ม "เข้าร่วม" บนการ์ด "เขตลับโปเกมอน" (550, 460)
   - ตรวจสอบโซน: หากยังอยู่โซนระดับสูง ให้กดสลับไป "โซนธรรมดา" (1120, 410)
   - กดเปิดแถบ "การจับอัตโนมัติ" (875, 655)
   - กดปุ่ม "เริ่มจับ" (835, 680)
   - วนกลับสู่ Phase 1 ต่อเนื่อง
"""

import os
import sys
import time
import cv2
from datetime import datetime
from typing import Optional, Tuple

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from core.adb_client import AdbClient
from core.vision import Vision

# ============================================================
# COORDINATES & CONSTANTS (1280x720 Native Resolution)
# ============================================================

# Phase 1: Secret Realm Catching
CATCH_AGAIN_COORDS = (752, 559)
DIALOG_OK_COORDS = (647, 419)
DIALOG_CANCEL_COORDS = (550, 395)       # ปุ่ม "ยกเลิก" บนป๊อปอัปคำเตือนสัตว์เลี้ยงผูกพัน (การ์เดียนเพท)
CATCH_CLOSE_COORDS = (526, 563)
TOP_RIGHT_CLOSE_X = (1240, 40)         # กากบาทมุมขวาบน (ทั้งในเขตลับ, หน้าฝึกซ้อม และหน้าโปเกมอน)
HOME_BUTTON_COORDS = (1245, 80)        # ปุ่ม Home (กรณีติดหน้าผจญภัยแผนที่โลก)

# Phase 2: Pokemon Inventory & Fusion
LOBBY_POKEMON_BTN = (1150, 660)        # ปุ่ม "โปเกมอน" ขวาล่างใน Lobby
TARGET_POKEMON_SLOT_5 = (1100, 280)    # W.Kyurem (Slot 5)
TAB_TRAIN_BTN = (1230, 487)            # แท็บ "ฝึก"

FUSION_COLS = [790, 890, 1000, 1100]
FUSION_ROWS = [440, 530, 620]
FUSION_CONFIRM_BTN = (1065, 670)       # ปุ่มสีทอง "รวม"

# Phase 3: Navigation to Secret Realm
LOBBY_TRAIN_BTN = (1170, 70)           # ปุ่ม "ฝึก" ขวาบนใน Lobby (ตรงกลางระหว่างเรื่องราวกับผจญภัย)
TAB_ADVENTURE_BTN = (80, 380)          # แท็บ "ผจญภัย" (แว่นขยาย)
SECRET_REALM_JOIN_BTN = (585, 451)     # ปุ่ม "เข้าร่วม" บนการ์ดเขตลับโปเกมอน (กึ่งกลางปุ่มสีทอง 585, 451)
SWITCH_TO_NORMAL_ZONE_BTN = (1120, 410)# ปุ่ม "<<< กดไปยัง โซนธรรมดา"
AUTO_CATCH_DIAMOND_BTN = (875, 655)    # แถบสี่เหลี่ยมข้าวหลามตัด "การจับอัตโนมัติ"
START_CATCH_BTN = (835, 680)           # ปุ่มสีทอง "เริ่มจับ"


class SecretRealmBot:
    def __init__(self):
        print(f"\n{'='*60}", flush=True)
        print(" [MonsterBot] Secret Realm Auto Farm & Fusion Loop Initializing", flush=True)
        print(f"{'='*60}\n", flush=True)
        self.adb = AdbClient()
        self.vision = Vision(os.path.join(BASE_DIR, "templates"))

        # Statistics
        self.total_loops = 0
        self.total_catches = 0
        self.total_fusions = 0
        self.start_time = time.time()

    def log(self, tag: str, msg: str):
        now = datetime.now().strftime("%H:%M:%S")
        print(f"[{now}] [{tag}] {msg}", flush=True)

    # ============================================================
    # SCREEN CHECKS & HELPERS
    # ============================================================

    def is_bag_full_dialog(self, img) -> bool:
        """ตรวจจับป๊อปอัปแจ้งเตือนกระเป๋าเต็ม (ปุ่มตกลง)"""
        match = self.vision.match(img, "dialog_ok_button.png", threshold=0.88)
        return match is not None

    def is_catch_again_visible(self, img) -> Optional[Tuple[int, int]]:
        """ตรวจจับปุ่ม 'จับอีกครั้ง'"""
        match = self.vision.match(img, "catch_again_button.png", threshold=0.88)
        if match:
            return (match[0], match[1])
        return None

    def is_warning_dialog(self, img) -> bool:
        """ตรวจจับป๊อปอัปคำเตือนสัตว์เลี้ยงผูกพัน (ปุ่มยกเลิก / ป้ายคำเตือน)"""
        if self.vision.match(img, "dialog_cancel_button.png", threshold=0.82):
            return True
        if self.vision.match(img, "dialog_warning_box.png", threshold=0.82):
            return True
        return False

    def is_guardian_pet_visible(self, img) -> bool:
        """ตรวจจับป้ายข้อความ 'การ์เดียนเพท' เฉพาะในพื้นที่ตารางเลือกโปเกมอน 12 ช่อง (ROI) หรือเมื่อมีป๊อปอัปคำเตือน"""
        if self.is_warning_dialog(img):
            return True
        # ROI ของตารางเลือกโปเกมอน: x: 740..1160, y: 360..680
        match = self.vision.match(img, "guardian_pet_text.png", threshold=0.80, roi=(740, 360, 1160, 680))
        return match is not None

    def is_lobby(self, img) -> bool:
        """ตรวจจับหน้า Lobby จากปุ่มฝึกขวาบน, ปุ่มเครื่องหมายบวกมุมขวาล่าง, หรือปุ่มจับคู่"""
        if self.vision.match(img, "lobby_train_btn_v2.png", threshold=0.88):
            return True
        if self.vision.match(img, "main_lobby_plus_btn.png", threshold=0.78):
            return True
        if self.vision.match(img, "match_button.png", threshold=0.85):
            return True
        return False

    def is_high_zone(self, img) -> bool:
        """ตรวจว่าปัจจุบันอยู่ในโซนระดับสูงหรือไม่ (มีปุ่มสลับไปโซนธรรมดา)"""
        match = self.vision.match(img, "switch_to_normal_zone_final.png", threshold=0.82)
        return match is not None

    def is_secret_realm(self, img) -> bool:
        """ตรวจสอบว่าหน้าจอปัจจุบันคือเขตลับโปเกมอนจริงหรือไม่ (ป้องกันการหลุดไปโหมดอื่น)"""
        if self.is_high_zone(img):
            return True
        if self.vision.match(img, "auto_catch_diamond.png", threshold=0.85):
            return True
        if self.vision.match(img, "start_catch_button.png", threshold=0.85):
            return True
        if self.is_catch_again_visible(img):
            return True
        return False

    def find_secret_realm_join_btn(self, img) -> Optional[Tuple[int, int]]:
        """สแกนหาการ์ด 'เขตลับโปเกมอน' และคำนวณพิกัดปุ่ม 'เข้าร่วม' ของการ์ดนั้นโดยตรง"""
        tpl_path = os.path.join(BASE_DIR, "templates", "title_secret_realm_full.png")
        if not os.path.exists(tpl_path):
            return None
        tpl = cv2.imread(tpl_path, cv2.IMREAD_GRAYSCALE)
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        res = cv2.matchTemplate(gray, tpl, cv2.TM_CCOEFF_NORMED)
        min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(res)
        if max_val >= 0.78:
            loc_x, loc_y = max_loc
            btn_x = loc_x - 10
            btn_y = loc_y + 140
            return (btn_x, btn_y)
        return None

    def ensure_lobby(self, max_attempts: int = 6):
        """กดปิดหน้าต่างย้อนกลับจนกว่าจะถึงหน้า Lobby"""
        self.log("NAV", "กำลังเดินทาง/ย้อนกลับสู่หน้า Lobby...")
        for i in range(max_attempts):
            img = self.adb.screencap()
            if self.is_lobby(img):
                self.log("NAV", f"ถึงหน้า Lobby เรียบร้อยแล้ว (รอบที่ {i+1})")
                return True
            # ถ้ามีป๊อปอัปคำเตือนบล็อกอยู่ ให้กด "ยกเลิก" ทันที
            if self.is_warning_dialog(img):
                self.log("NAV", "ตรวจพบป๊อปอัปคำเตือนบล็อกหน้าจอ กดปุ่ม 'ยกเลิก'...")
                self.adb.tap(*DIALOG_CANCEL_COORDS)
                time.sleep(0.8)
                continue
            # ถ้ามีปุ่ม Home บนแผนที่โลก
            if self.vision.match(img, "world_map_home.png", threshold=0.82):
                self.log("NAV", "ตรวจพบหน้าต่างแผนที่โลก กดปุ่ม Home เพื่อกลับ Lobby...")
                self.adb.tap(*HOME_BUTTON_COORDS)
                time.sleep(1.8)
                continue
            # กากบาทมุมขวาบน (1240, 40)
            self.adb.tap(*TOP_RIGHT_CLOSE_X)
            time.sleep(1.2)
        return False

    # ============================================================
    # PHASE 1: CATCH POKEMON UNTIL BAG IS FULL
    # ============================================================

    def run_catch_phase(self) -> bool:
        self.log("PHASE 1", "=== เริ่มต้น Phase 1: ฟาร์มจับโปเกมอนในเขตลับ (โซนธรรมดา) ===")
        no_action_count = 0
        phase_catches = 0

        while True:
            img = self.adb.screencap()

            # 1. เช็คว่ามีป๊อปอัปแจ้งเตือนกระเป๋าเต็มหรือไม่
            if self.is_bag_full_dialog(img):
                self.log("PHASE 1", ">> ตรวจพบป๊อปอัปกระเป๋าเต็ม (120/120)! เริ่มกระบวนการเคลียร์กระเป๋า <<")
                # กด "ตกลง"
                self.log("PHASE 1", f"กดปุ่ม 'ตกลง' ที่ {DIALOG_OK_COORDS}")
                self.adb.tap(*DIALOG_OK_COORDS)
                time.sleep(0.6)

                # กด "ปิด" ป๊อปอัปผลการจับ
                self.log("PHASE 1", f"กดปุ่ม 'ปิด' ป๊อปอัปผลการจับ ที่ {CATCH_CLOSE_COORDS}")
                self.adb.tap(*CATCH_CLOSE_COORDS)
                time.sleep(0.8)

                # ออกจากหน้าจอเขตลับกลับสู่ Lobby
                self.log("PHASE 1", f"กดกากบาท (X) ออกจากเขตลับ ที่ {TOP_RIGHT_CLOSE_X}")
                self.adb.tap(*TOP_RIGHT_CLOSE_X)
                time.sleep(1.0)

                self.ensure_lobby()
                self.log("PHASE 1", f"จบ Phase 1 รอบนี้จับได้ทั้งหมด {phase_catches} ตัว")
                return True

            # 2. เช็คปุ่ม "จับอีกครั้ง"
            catch_pos = self.is_catch_again_visible(img)
            if catch_pos:
                target_pos = catch_pos if catch_pos else CATCH_AGAIN_COORDS
                self.adb.tap(*target_pos)
                self.total_catches += 1
                phase_catches += 1
                no_action_count = 0
                if phase_catches % 5 == 0 or phase_catches == 1:
                    self.log("PHASE 1", f"กดจับอีกครั้ง (ครั้งที่ {phase_catches}, สะสมทั้งหมด: {self.total_catches})")
                time.sleep(0.45)
                continue

            # 3. เช็คปุ่ม "เริ่มจับ" (กรณีเพิ่งเปิดเข้ามาหน้าเขตลับ)
            start_btn = self.vision.match(img, "start_catch_button.png", threshold=0.88)
            if start_btn:
                self.log("PHASE 1", f"พบปุ่ม 'เริ่มจับ' กดที่ ({start_btn[0]}, {start_btn[1]})")
                self.adb.tap(start_btn[0], start_btn[1])
                no_action_count = 0
                time.sleep(1.5)
                continue

            # 4. เช็คแถบสี่เหลี่ยมข้าวหลามตัด "การจับอัตโนมัติ" ที่ยังพับอยู่ หรือติดค้าง
            if not catch_pos and not start_btn:
                no_action_count += 1
                if no_action_count == 2:
                    diamond_match = self.vision.match(img, "auto_catch_diamond.png", threshold=0.85)
                    tap_pos = (diamond_match[0], diamond_match[1]) if diamond_match else AUTO_CATCH_DIAMOND_BTN
                    self.log("PHASE 1", f"ลองแตะเปิดแถบ 'การจับอัตโนมัติ' ที่ {tap_pos}...")
                    self.adb.tap(*tap_pos)
                    time.sleep(1.0)
                elif no_action_count == 5:
                    self.log("PHASE 1", "[WARN] ไม่พบปุ่มควบคุมการจับ กำลังตรวจสอบหน้าจอ...")
                    time.sleep(0.8)
                elif no_action_count >= 8:
                    # ตรวจสอบว่ายังอยู่ในหน้าเขตลับจริงหรือไม่
                    if not self.is_secret_realm(img):
                        self.log("PHASE 1", "[CIRCUIT BREAKER] ตรวจพบไม่ได้อยู่ในหน้าเขตลับ (หลุดไปโหมดอื่น)! สั่งกด [X] ออกทันที...")
                        self.adb.tap(*TOP_RIGHT_CLOSE_X)
                        time.sleep(1.0)
                        self.adb.tap(*TOP_RIGHT_CLOSE_X)
                        time.sleep(1.2)
                        self.ensure_lobby()
                        return False

                    if no_action_count >= 15:
                        self.log("PHASE 1", "[CIRCUIT BREAKER] ไม่พบปุ่มควบคุมการจับนานเกิน 15 วินาที กำลังรีเซ็ตกลับสู่ Lobby...")
                        self.adb.tap(*TOP_RIGHT_CLOSE_X)
                        time.sleep(1.0)
                        self.adb.tap(*TOP_RIGHT_CLOSE_X)
                        time.sleep(1.2)
                        self.ensure_lobby()
                        return False

            time.sleep(0.2)

    # ============================================================
    # PHASE 2: FUSION & LEVEL UP POKEMON
    # ============================================================

    def run_fusion_phase(self) -> bool:
        self.log("PHASE 2", "=== เริ่มต้น Phase 2: รวมเลเวลโปเกมอน & เคลียร์กระเป๋า ===")

        # 1. จาก Lobby กดปุ่ม "โปเกมอน"
        self.log("PHASE 2", f"กดปุ่ม 'โปเกมอน' ที่ {LOBBY_POKEMON_BTN}")
        self.adb.tap(*LOBBY_POKEMON_BTN)
        time.sleep(1.2)

        # 2. เลือกโปเกมอนตัวหลัก (ตัวที่ 5 - W.Kyurem)
        self.log("PHASE 2", f"แตะเลือกโปเกมอนเป้าหมายหลัก ที่ {TARGET_POKEMON_SLOT_5}")
        self.adb.tap(*TARGET_POKEMON_SLOT_5)
        time.sleep(0.6)

        # 3. กดแท็บ "ฝึก"
        self.log("PHASE 2", f"กดแท็บ 'ฝึก' ด้านขวา ที่ {TAB_TRAIN_BTN}")
        self.adb.tap(*TAB_TRAIN_BTN)
        time.sleep(1.0)

        # 4. วนลูปรวมเลเวล (Sub-loop)
        fusion_rounds = 0
        max_fusion_rounds = 15

        while fusion_rounds < max_fusion_rounds:
            img = self.adb.screencap()

            # 1. ตรวจสอบป๊อปอัปคำเตือนสัตว์เลี้ยงผูกพัน (บล็อกทันที: กด 'ยกเลิก' เพื่อไม่ให้สูญเสียสัตว์เลี้ยง)
            if self.is_warning_dialog(img):
                self.log("PHASE 2", ">> [BLOCK] ตรวจพบป๊อปอัปคำเตือนสัตว์เลี้ยงผูกพัน! กด 'ยกเลิก' ทันทีและหยุดการรวม <<")
                self.adb.tap(*DIALOG_CANCEL_COORDS)
                time.sleep(0.6)
                break

            # 2. ป้องกันกรณีมีป๊อปอัปแจ้งเตือนกระเป๋าเต็ม
            if self.is_bag_full_dialog(img):
                self.log("PHASE 2", ">> ตรวจพบป๊อปอัปแจ้งเตือนในหน้าเลือกโปเกมอน กดตกลงและหยุดการรวมทันที <<")
                self.adb.tap(*DIALOG_OK_COORDS)
                time.sleep(0.8)
                break

            # 3. ตรวจสอบการ์เดียนเพท
            if self.is_guardian_pet_visible(img):
                self.log("PHASE 2", ">> ตรวจพบ 'การ์เดียนเพท' ในรายการแล้ว! หยุดการรวมโปเกมอนทันที <<")
                break

            self.log("PHASE 2", f"เริ่มเลือกโปเกมอน 12 ช่องเพื่อรวมเลเวล (รอบที่ {fusion_rounds + 1})...")

            # แตะเลือก 12 ช่อง (แถวละ 4 ตัว x 3 แถว)
            for y in FUSION_ROWS:
                for x in FUSION_COLS:
                    self.adb.tap(x, y, jitter=False)
                    time.sleep(0.04)

            time.sleep(0.04)

            # กดปุ่มสีทอง "รวม"
            self.log("PHASE 2", f"กดปุ่มสีทอง 'รวม' ที่ {FUSION_CONFIRM_BTN}")
            self.adb.tap(*FUSION_CONFIRM_BTN)
            fusion_rounds += 1
            self.total_fusions += 1
            time.sleep(0.45)

        self.log("PHASE 2", f"รวมโปเกมอนเสร็จสิ้นในรอบนี้: {fusion_rounds} ชุด (สะสมทั้งหมด: {self.total_fusions})")

        # 5. ออกจากหน้าโปเกมอนกลับสู่ Lobby
        self.log("PHASE 2", "กดกากบาท (X) กลับสู่หน้า Lobby...")
        self.adb.tap(*TOP_RIGHT_CLOSE_X)
        time.sleep(0.7)
        self.adb.tap(*TOP_RIGHT_CLOSE_X)
        time.sleep(1.0)
        self.ensure_lobby()
        return True

    # ============================================================
    # PHASE 3: RETURN TO SECRET REALM (NORMAL ZONE)
    # ============================================================

    def run_navigation_phase(self) -> bool:
        self.log("PHASE 3", "=== เริ่มต้น Phase 3: เดินทางกลับเข้าเขตลับ (โซนธรรมดา) ===")

        # 1. กดปุ่ม "ฝึก" ขวาบนใน Lobby
        self.log("PHASE 3", f"กดปุ่ม 'ฝึก' ขวาบน ที่ {LOBBY_TRAIN_BTN}")
        self.adb.tap(*LOBBY_TRAIN_BTN)
        time.sleep(1.2)

        # 2. กดแท็บ "ผจญภัย"
        self.log("PHASE 3", f"กดแท็บ 'ผจญภัย' ที่ {TAB_ADVENTURE_BTN}")
        self.adb.tap(*TAB_ADVENTURE_BTN)
        time.sleep(1.2)

        # 3. ค้นหาการ์ด "เขตลับโปเกมอน" โดยเลื่อนหน้าจอ
        target_join_btn = None
        for scroll_i in range(3):
            # ตรวจสอบก่อนว่าการ์ดปรากฏบนหน้าจอแล้วหรือไม่
            img = self.adb.screencap()
            btn_pos = self.find_secret_realm_join_btn(img)
            if btn_pos:
                target_join_btn = btn_pos
                self.log("PHASE 3", f">> ตรวจพบการ์ดเขตลับโปเกมอน! ปุ่ม 'เข้าร่วม' อยู่ที่ {target_join_btn} <<")
                break

            # หากยังไม่พบ ให้เลื่อนหน้าจอขึ้น
            self.log("PHASE 3", f"เลื่อนหน้าจอค้นหาการ์ด 'เขตลับโปเกมอน' (ครั้งที่ {scroll_i + 1})...")
            self.adb.swipe(500, 580, 500, 200, duration_ms=350)
            time.sleep(1.0)

            # ตรวจสอบอีกครั้งหลังเลื่อน
            img = self.adb.screencap()
            btn_pos = self.find_secret_realm_join_btn(img)
            if btn_pos:
                target_join_btn = btn_pos
                self.log("PHASE 3", f">> ตรวจพบการ์ดเขตลับโปเกมอน! ปุ่ม 'เข้าร่วม' อยู่ที่ {target_join_btn} <<")
                break

        # ป้องกันการแตะมั่ว: หากไม่พบการ์ด ห้ามกดสุ่มเด็ดขาด ให้ถอยกลับสู่ Lobby อย่างปลอดภัย
        if not target_join_btn:
            self.log("PHASE 3", "[WARN] ไม่พบการ์ดเขตลับโปเกมอน! ยกเลิกและกลับสู่ Lobby ทันทีเพื่อป้องกันการหลุดเข้าโหมดอื่น")
            self.adb.tap(*TOP_RIGHT_CLOSE_X)
            time.sleep(0.8)
            self.ensure_lobby()
            return False

        # 4. กดปุ่ม "เข้าร่วม" บนการ์ด "เขตลับโปเกมอน"
        self.log("PHASE 3", f"กดปุ่ม 'เข้าร่วม' เขตลับ ที่ {target_join_btn}")
        self.adb.tap(*target_join_btn)
        time.sleep(2.5)

        # 5. Safety Gate: ตรวจสอบยืนยันว่าเข้าสู่เขตลับจริงหรือไม่
        in_realm = False
        for wait_i in range(6):
            check_img = self.adb.screencap()
            if self.is_secret_realm(check_img):
                in_realm = True
                break
            time.sleep(0.8)

        if not in_realm:
            self.log("PHASE 3", "[ALERT] ไม่พบหน้าจอเขตลับ (อาจเข้าผิดโหมดหรือหน้าจอค้าง)! สั่งกด [X] ออกทันทีเพื่อความปลอดภัย...")
            self.adb.tap(*TOP_RIGHT_CLOSE_X)
            time.sleep(1.0)
            self.adb.tap(*TOP_RIGHT_CLOSE_X)
            time.sleep(1.0)
            self.ensure_lobby()
            return False

        # 6. ตรวจสอบสถานะโซน (ถ้าอยู่โซนระดับสูง ให้สลับไปโซนธรรมดา)
        img = self.adb.screencap()
        if self.is_high_zone(img):
            self.log("PHASE 3", f"ตรวจพบอยู่ในโซนระดับสูง! กดสลับไปยัง 'โซนธรรมดา' ที่ {SWITCH_TO_NORMAL_ZONE_BTN}")
            self.adb.tap(*SWITCH_TO_NORMAL_ZONE_BTN)
            time.sleep(1.2)
        else:
            self.log("PHASE 3", "ยืนยันสถานะ: อยู่ใน 'โซนธรรมดา' เรียบร้อยแล้ว")

        # 7. เปิดแถบ "การจับอัตโนมัติ" และกด "เริ่มจับ"
        img = self.adb.screencap()
        start_btn = self.vision.match(img, "start_catch_button.png", threshold=0.85)
        if not start_btn:
            self.log("PHASE 3", f"กดเปิดแถบ 'การจับอัตโนมัติ' ที่ {AUTO_CATCH_DIAMOND_BTN}")
            self.adb.tap(*AUTO_CATCH_DIAMOND_BTN)
            time.sleep(0.8)
            img = self.adb.screencap()
            start_btn = self.vision.match(img, "start_catch_button.png", threshold=0.85)

        target_start = (start_btn[0], start_btn[1]) if start_btn else START_CATCH_BTN
        self.log("PHASE 3", f"กดปุ่ม 'เริ่มจับ' ที่ {target_start}")
        self.adb.tap(*target_start)
        time.sleep(1.5)

        self.log("PHASE 3", "เริ่มการจับอัตโนมัติเรียบร้อยแล้ว พร้อมเข้าสู่ Phase 1")
        return True

        self.log("PHASE 3", "เริ่มการจับอัตโนมัติเรียบร้อยแล้ว พร้อมเข้าสู่ Phase 1")
        return True

    # ============================================================
    # MASTER LOOP
    # ============================================================

    def run(self):
        self.log("MAIN", "เริ่มต้นระบบลูปอัตโนมัติแบบ Full Loop...")
        print(f"{'-'*60}")
        print(" [CTRL+C เพื่อหยุดการทำงานอย่างปลอดภัยได้ทุกเมื่อ]")
        print(f"{'-'*60}\n")

        try:
            # ตรวจสอบสถานะหน้าจอเริ่มต้น
            initial_img = self.adb.screencap()

            # ถ้าอยู่ที่หน้าผลการจับอยู่แล้ว สามารถเริ่ม Phase 1 ได้ทันที
            if self.is_catch_again_visible(initial_img):
                self.log("MAIN", "ตรวจพบหน้าต่าง 'จับสำเร็จ' กำลังรัน Phase 1 ทันที...")
            elif self.is_secret_realm(initial_img):
                self.log("MAIN", "ตรวจพบอยู่ในเขตลับเรียบร้อยแล้ว พร้อมเริ่ม Phase 1...")
            else:
                self.log("MAIN", "นำทางเข้าสู่เขตลับโปเกมอน...")
                self.ensure_lobby()
                while not self.run_navigation_phase():
                    self.log("MAIN", "[WARN] นำทางเข้าเขตลับไม่สำเร็จ กำลังลองใหม่ใน 2 วินาที...")
                    self.ensure_lobby()
                    time.sleep(2.0)

            while True:
                self.total_loops += 1
                loop_start = time.time()
                self.log("LOOP", f"========== [ เริ่มต้นรอบที่ {self.total_loops} ] ==========")

                # Step 1: จับโปเกมอนจนกระเป๋าเต็ม
                catch_ok = self.run_catch_phase()
                if not catch_ok:
                    self.log("LOOP", "[WARN] Phase 1 หลุดออกจากเขตลับหรือไม่สำเร็จ นำทางเข้าเขตลับใหม่...")
                    while not self.run_navigation_phase():
                        self.log("LOOP", "[WARN] กำลังพยายามนำทางเข้าเขตลับใหม่...")
                        self.ensure_lobby()
                        time.sleep(2.0)
                    continue

                # Step 2: รวมเลเวล & เคลียร์กระเป๋า
                self.run_fusion_phase()

                # Step 3: กลับเข้าเขตลับ โซนธรรมดา & เริ่มจับ
                while not self.run_navigation_phase():
                    self.log("LOOP", "[WARN] นำทางเข้าเขตลับไม่สำเร็จ กำลังลองใหม่...")
                    self.ensure_lobby()
                    time.sleep(2.0)

                elapsed_loop = time.time() - loop_start
                total_elapsed = time.time() - self.start_time
                self.log("LOOP", f"=== จบรอบที่ {self.total_loops} (ใช้เวลา: {elapsed_loop:.1f}s | เวลารวม: {total_elapsed/60:.1f} นาที) ===")
                self.log("LOOP", f"=== สถิติ: จับโปเกมอนไปแล้ว {self.total_catches} ครั้ง | รวมเลเวล {self.total_fusions} ชุด ===")
                time.sleep(1.0)

        except KeyboardInterrupt:
            total_elapsed = time.time() - self.start_time
            print(f"\n\n{'='*60}")
            self.log("MAIN", "ผู้ใช้สั่งหยุดการทำงาน (Ctrl+C)")
            self.log("MAIN", f"สรุปผลการรัน: จบลูปทั้งหมด {self.total_loops} รอบ")
            self.log("MAIN", f"สถิติจับโปเกมอน: {self.total_catches} ครั้ง | รวมเลเวล: {self.total_fusions} ชุด")
            self.log("MAIN", f"เวลารวมทั้งหมด: {total_elapsed/60:.2f} นาที")
            print(f"{'='*60}\n")


if __name__ == "__main__":
    bot = SecretRealmBot()
    bot.run()
