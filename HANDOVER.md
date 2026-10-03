# MonsterBot Handover & Development Guide

เอกสารสรุปภาพรวมโครงสร้างบอท สถานะปัจจุบัน และแนวทางการพัฒนาฟีเจอร์ต่อยอด (Handover Documentation) สำหรับโปรเจกต์ **MonsterBot**

---

## 📌 สารบัญ (Table of Contents)
1. [ภาพรวมระบบและสถานะปัจจุบัน (Overview & Current Status)](#1-ภาพรวมระบบและสถานะปัจจุบัน)
2. [โครงสร้างไฟล์และสคริปต์ในโปรเจกต์ (Project Structure)](#2-โครงสร้างไฟล์และสคริปต์ในโปรเจกต์)
3. [ตารางพิกัดและค่า Threshold สำคัญ (Key Coordinates & Thresholds)](#3-ตารางพิกัดและค่า-threshold-สำคัญ)
4. [การทำงานของ State Machine ใน bot.py](#4-การทำงานของ-state-machine-ใน-botpy)
5. [แนวทางการพัฒนาต่อยอด พร้อมตัวอย่างโค้ด (Roadmap & Implementation Guide)](#5-แนวทางการพัฒนาต่อยอด-พร้อมตัวอย่างโค้ด)
   - [5.1 ระบบแจ้งเตือน Discord Webhook (พร้อมภาพแคปหน้าจอ)](#51-ระบบแจ้งเตือน-discord-webhook)
   - [5.2 ระบบ Auto-Recovery เปิดเกมใหม่อัตโนมัติเมื่อเกมหลุด](#52-ระบบ-auto-recovery-เปิดเกมใหม่อัตโนมัติเมื่อเกมหลุด)
   - [5.3 ระบบบันทึกสถิติการฟาร์มลงไฟล์ CSV (Stats Tracker)](#53-ระบบบันทึกสถิติการฟาร์มลงไฟล์-csv)
   - [5.4 ระบบปุ่มลัดคีย์บอร์ด (Hotkeys Pause / Stop ด้วย F8 / F9)](#54-ระบบปุ่มลัดคีย์บอร์ด-hotkeys)
   - [5.5 การแยกคอนฟิกออกเป็น config.json](#55-การแยกคอนฟิกออกเป็น-configjson)
6. [วิธีรัน การทดสอบ และการแก้ปัญหาทั่วไป (Run & Troubleshooting)](#6-วิธีรัน-การทดสอบ-และการแก้ปัญหาทั่วไป)

---

## 1. ภาพรวมระบบและสถานะปัจจุบัน

- **เกมเป้าหมาย**: Monster Saga
- **อีมูเลเตอร์**: MuMuPlayer
- **ADB Path**: `C:\Program Files\Netease\MuMuPlayer\nx_main\adb.exe`
- **Device Port**: `127.0.0.1:5559`
- **ความละเอียดหน้าจอ (Native Resolution)**: `1280 x 720` (DPI: 240)
- **สถานะปัจจุบัน**:
  - บอททำงานได้เสถียร (Loop ทำงานได้ต่อเนื่อง ครบวงจรตั้งแต่ Lobby -> จับคู่ -> เลือกตัวละคร 3 Wave -> ต่อสู้ Unified Loop -> กลับสู่ Lobby)
  - มีระบบ Auto-Reconnect ADB เมื่อสัญญาณหลุด
  - มีระบบ HSV Color Detection ตรวจจับปุ่ม AUTO สีฟ้า (OFF) และสีเหลือง (ON)
  - มีระบบ Template Matching ตรวจสอบปุ่ม "กลับ" และปุ่ม "ต่อไป"
  - มีระบบ Circuit Breaker (Watchdog 16 นาที) ป้องกันบอทติดลูปตายในแมตช์

## 2. โครงสร้างไฟล์และสคริปต์ในโปรเจกต์

```text
C:\MonsterBot\
│
├── champ_bot.py             # [บอทแชมป์ Season 1] โหมด 3 Wave (เลือก 3-3-3 ตัว, Auto ทุก Wave)
├── champ_bot_season2.py     # [บอทแชมป์ Season 2] โหมด 3 Wave (เลือก 1-2-3 ตัว, Wave 1 บังคับ Manual + กดสกิล, Wave 2-3 Auto)
├── secret_realm_bot.py      # [บอทเขตลับ & รวมเลเวล] จับโปเกมอนโซนธรรมดาจนกระเป๋าเต็ม (120/120) -> รวมเลเวล W.Kyurem (ตรวจจับการ์เดียนเพท) -> วนกลับเข้าเขตลับ
├── master_bot.py            # [บอทหลัก] ควบคุมและรัน Task ทั้งหมดแบบ Full-Game Autonomous
├── tower_bot.py             # [บอททาวเวอร์] โหมดทาวเวอร์ต่อสู้ ไต่หอคอย 80 ชั้น (โหมด Easy)
├── tower_hard_bot.py        # [บอททาวเวอร์ Hard] โหมดท้าทาย ซื้อบัฟตาม Priority สู้ทีมหลาย Wave จบชั้น 80
├── screenshot.py            # [เครื่องมือ] สคริปต์แคปภาพหน้าจอเกมผ่าน ADB บันทึกลง screenshots/
├── AGENTS.md                # [กฎ & กติกา] กฎเหล็ก Game Flow Discovery และข้อปฏิบัติประจำโปรเจกต์
├── HANDOVER.md              # [เอกสาร] สรุปงาน คู่มือ และแนวทางพัฒนาต่อยอด (ไฟล์นี้)
│
├── templates/               # โฟลเดอร์เก็บภาพ Template ที่จำเป็นสำหรับบอท
│   ├── match_button.png     # ภาพปุ่ม Match ในหน้า Lobby
│   ├── next_wave_button.png # ภาพข้อความปุ่ม "ต่อไป" ระหว่าง Wave
│   ├── return_button.png    # ภาพข้อความปุ่ม "กลับ" ตอนจบแมตช์
│   ├── catch_again_button.png # ภาพปุ่ม "จับอีกครั้ง" ในเขตลับ
│   ├── dialog_ok_button.png # ภาพปุ่ม "ตกลง" แจ้งเตือนกระเป๋าเต็ม
│   ├── catch_close_button.png # ภาพปุ่ม "ปิด" สรุปผลการจับ
│   ├── guardian_pet_text.png # ภาพป้าย "การ์เดียนเพท" (เงื่อนไขหยุดรวมเลเวล)
│   ├── start_catch_button.png # ภาพปุ่ม "เริ่มจับ" ในเขตลับ
│   ├── top_right_close_x.png # ภาพปุ่มกากบาท (X) มุมขวาบน
│   ├── badge_floor_80.png   # ภาพป้ายแดงชั้น 80 สำหรับโหมด Hard
│   └── badge_normal_80.png  # ภาพป้ายน้ำเงินชั้น 80 สำหรับโหมดธรรมดา
│
└── screenshots/             # โฟลเดอร์เก็บภาพ Screenshot (สำหรับดู debug เมื่อจำเป็น)
```

---

## 3. ตารางพิกัดและค่า Threshold สำคัญ

### พิกัดคลิกสำหรับโหมดฟาร์มเขตลับ & รวมเลเวล (secret_realm_bot.py)
| ตำแหน่ง / ปุ่ม | พิกัด (X, Y) | รายละเอียด |
| :--- | :--- | :--- |
| **CATCH_AGAIN** | `(752, 559)` | ปุ่มสีทอง "จับอีกครั้ง" ในหน้าผลลัพธ์การจับเขตลับ |
| **BAG_FULL_OK** | `(647, 419)` | ปุ่ม "ตกลง" บนป๊อปอัปแจ้งเตือนกระเป๋าเต็ม (120/120) |
| **CATCH_CLOSE** | `(526, 563)` | ปุ่มสีฟ้า "ปิด" หน้าต่างสรุปผลการจับ |
| **TOP_RIGHT_CLOSE_X** | `(1240, 40)` | ปุ่มกากบาท (X) มุมขวาบน สำหรับออกจากหน้าต่าง/กลับ Lobby |
| **LOBBY_POKEMON** | `(1150, 660)` | ปุ่ม "โปเกมอน" มุมขวาล่างในหน้า Lobby (ไอคอนมังกรแดง) |
| **TARGET_POKEMON_SLOT_5** | `(1100, 280)` | แตะโปเกมอนตัวเป้าหมายที่จะอัปเกรด (ตัวที่ 5 - W.Kyurem) |
| **TAB_TRAIN** | `(1230, 487)` | แท็บ "ฝึก" ขวากลางล่างในหน้ารายละเอียดโปเกมอน |
| **FUSION_SLOTS (12 ช่อง)** | X: `[790, 890, 1000, 1100]`<br>Y: `[440, 530, 620]` | 12 ช่องเลือกโปเกมอนที่จะนำมารวมเลเวล (4 คอลัมน์ x 3 แถว) |
| **FUSION_CONFIRM** | `(1065, 670)` | ปุ่มสีทอง "รวม" เพื่อยืนยันการเพิ่มเลเวล |
| **GUARDIAN_PET_CHECK** | Template `guardian_pet_text.png` | ตรวจสอบคำว่า "การ์เดียนเพท" หากเจอต้องหยุดรวมทันที |
| **LOBBY_TRAIN_BTN** | `(1170, 70)` | ปุ่ม "ฝึก" มุมขวาบนใน Lobby (ตรงกลางระหว่างเรื่องราวและผจญภัย) |
| **TAB_ADVENTURE** | `(80, 380)` | แท็บ "ผจญภัย" ด้านซ้ายมือ (ไอคอนแว่นขยาย) |
| **SWIPE_ADVENTURE** | `(500, 580) -> (500, 220)` | เลื่อนจอลงเพื่อแสดงการ์ด "เขตลับโปเกมอน" |
| **SECRET_REALM_JOIN** | `(585, 451)` | ปุ่ม "เข้าร่วม" บนการ์ดเขตลับโปเกมอน (กึ่งกลางปุ่มสีทอง หลังเลื่อน Swipe) |
| **SWITCH_TO_NORMAL** | `(1120, 410)` | ปุ่ม "<<< กดไปยัง โซนธรรมดา" เมื่ออยู่โซนระดับสูง |
| **AUTO_CATCH_DIAMOND** | `(875, 655)` | ปุ่มข้าวหลามตัด "การจับอัตโนมัติ" (Template `auto_catch_diamond.png`) เพื่อกางแถบเมนู |
| **START_CATCH** | `(835, 680)` | ปุ่มสีทอง "เริ่มจับ" ในแถบการจับอัตโนมัติ (Template `start_catch_button.png`) |

### พิกัดคลิก (Coordinates on 1280x720)
| ตำแหน่ง / ปุ่ม | พิกัด (X, Y) | รายละเอียด |
| :--- | :--- | :--- |
| **MATCH** | `(756, 662)` | ปุ่มกดเริ่มจับคู่ในหน้า Lobby |
| **CHARACTERS** | `(272, 654)`, `(382, 654)`, `(492, 654)` | ตำแหน่งการ์ดตัวละคร 1, 2, 3 สำหรับลงทีม |
| **NEXT** | `(941, 492)` | ปุ่มกดถัดไป หลังเลือกทีม Wave 1 และ 2 |
| **BATTLE** | `(941, 492)` | ปุ่มเริ่มสู้ หลังเลือกทีม Wave 3 เสร็จสิ้น |
| **AUTO** | `(56, 160)` | ปุ่มเปิด Auto ตอนต่อสู้ |
| **RETURN** | `(635, 633)` | ปุ่ม "กลับ" เพื่อออกจากหน้าสรุปผลกลับสู่ Lobby |

### พิกัดคลิกสำหรับโหมดแชมเปี้ยน Season 2 (champ_bot_season2.py)
| ตำแหน่ง / ปุ่ม | พิกัด (X, Y) | รายละเอียด |
| :--- | :--- | :--- |
| **MATCH** | `(756, 662)` | ปุ่มกดเริ่มจับคู่ในหน้า Lobby |
| **CHARACTERS** | `(205, 670)`, `(305, 670)`, `(405, 670)` | ตำแหน่งการ์ดตัวละคร 1, 2, 3 สำหรับลงทีม Season 2 (Wave 1: 1ตัว, Wave 2: 2ตัว, Wave 3: 3ตัว) |
| **NEXT / BATTLE** | `(940, 490)` | ปุ่มหกเหลี่ยมสีฟ้า "ทีมต่อไป" และเริ่มสู้ |
| **SKILL_RED** | `(708, 627)` | สกิลกล่องสีแดง (ไฟ/อุกกาบาต) ของ Wave 1 (กดก่อน) |
| **SKILL_GREEN** | `(956, 625)` | สกิลกล่องสีเขียว (กรงเล็บ) ของ Wave 1 (กดทีหลัง) |
| **AUTO** | `(45, 240)` | ปุ่มต่อสู้ออโต้ (Wave 1 บังคับ OFF, Wave 2 และ 3 เปิด ON) |
| **RETURN** | `(635, 632)` | ปุ่ม "กลับ" เพื่อออกจากหน้าสรุปผลกลับสู่ Lobby |

### พิกัดคลิกสำหรับโหมดทาวเวอร์ Hard (tower_hard_bot.py)
| ตำแหน่ง / ปุ่ม | พิกัด (X, Y) | รายละเอียด |
| :--- | :--- | :--- |
| **TAB_CHALLENGE** | `(150, 185)` | แท็บ "ท้าทาย" (โหมด Hard) มุมซ้ายบน |
| **OPPONENT** | `(707, 520)` | แตะศัตรูที่ยืนบนแท่นตรงกลาง |
| **CHALLENGE_SINGLE** | `(638, 410)` | ปุ่ม "ท้าทาย" สีทอง ในหน้าต่างการต่อสู้ส่วนบุคคล (1 Wave) |
| **CHALLENGE_TEAM** | `(638, 495)` / `(660, 520)` | ปุ่ม "ท้าทาย" สีทอง ในหน้าต่างการต่อสู้ทีม (3 Wave) |
| **VICTORY_NEXT** | `(800, 630)` | ปุ่ม "ต่อไป" ในหน้าสรุปชัยชนะ |
| **BUFF_EMBLEM** | `(706, 586)` | แตะแท่นบัฟตรงกลางเพื่อเปิดหน้าต่าง "ซื้อbuff" |
| **BUFF_CARDS_X** | `304, 642, 980` | กึ่งกลางการ์ดบัฟ ใบที่ 1, 2, 3 (แถว Y=531) ซื้อบัฟทั่วไปก่อน ฮีลเขียวซื้อหลังสุด |
| **BUFF_CLOSE** | `(1230, 43)` | ปุ่มกากบาทปิดหน้าต่างบัฟ (จะกดเฉพาะตอนหน้าต่างบัฟยังค้างอยู่เท่านั้น หากซื้อครบ 3 ใบเกมจะปิดหน้าต่างอัตโนมัติ ห้ามกดซ้ำเพราะจะกลายเป็นปุ่มออกจากหอคอย) |
| **BUFF_CONFIRM_OK** | `(717, 411)` | ปุ่ม "ตกลง" เมื่อมีแจ้งเตือนยังมีบัฟค้าง |
| **CHEST_TARGET** | `(707, 600)` | แตะกล่องสมบัติบนแท่นตรงกลาง |
| **CHEST_DISMISS** | `(500, 460)` | แตะเพื่อปิดป๊อปอัปได้รับของรางวัล |
| **CHEST_LEAVE** | `(430, 575)` | ปุ่ม "ทิ้งไว้" เพื่อปิดหน้าต่างเปิดหีบโดยไม่เสียเพชร (Verified) |
| **BADGE_FLOOR_80** | Isolated Digits Match | สกัดตัวเลขสีเหลือง (HSV Mask) และตรวจสอบเลข '8' และ '0' แยกกันด้วย `digit_8.png` และ `digit_0.png` (Threshold > 0.88 แต่ละตัว) พร้อมเช็คเฉพาะเมื่อลิฟต์หยุดนิ่ง (ไม่ติด `TRANSITION`) ป้องกันการหลงชั้นอย่างชั้น 68 (match ~0.76) หรือ 69 (match ~0.32) |

### ค่าเกณฑ์ความแม่นยำ (Thresholds)
| ค่า Threshold | ค่าที่ตั้งไว้ | คำอธิบาย |
| :--- | :--- | :--- |
| `MATCH_THRESHOLD` | `0.90` | ค่าความมั่นใจในการเจอ Match Button (0.0 - 1.0) |
| `BUTTON_TYPE_THRESHOLD` | `0.88` | ค่าความมั่นใจในการจำแนกปุ่ม "กลับ" และ "ต่อไป" |
| `AUTO_BLUE_THRESHOLD` | `0.25` | ตรวจจับสีฟ้า/Cyan รอบปุ่ม AUTO (แปลว่า Auto ปิดอยู่) |
| `AUTO_YELLOW_THRESHOLD` | `0.08` | ตรวจจับสีเหลือง/Gold รอบปุ่ม AUTO (แปลว่า Auto เปิดอยู่) |
| `RESULT_THRESHOLD` | `0.25` | ตรวจจับสีทอง/ส้มของปุ่มหน้าสรุปผล |
| `REQUIRED_CONSECUTIVE_FRAMES` | `2` | ต้องตรวจเจอปุ่ม "กลับ" 2 เฟรมติดกัน ป้องกัน False Positive |

---

## 4. การทำงานของ State Machine ใน bot.py

```
[Start]
   │
   ▼
[State 1: Lobby] ────▶ รอเจอ MATCH_BUTTON (ถ้าติดหน้า Result บอทจะกด 'กลับ' ให้อัตโนมัติ)
   │
   ▼
[State 2: Match Searching] ────▶ รอ Screen Difference > 8 (มีคู่ต่อสู้เข้ามา)
   │
   ▼
[State 3: Team Selection]
   ├── Wave 1: เลือกตัว 1, 2, 3 ──▶ กด NEXT
   ├── Wave 2: เลือกตัว 1, 2, 3 ──▶ กด NEXT
   └── Wave 3: เลือกตัว 1, 2, 3 ──▶ กด BATTLE
   │
   ▼
[State 4: Unified Battle Loop]
   ├── รอหน้าจอ Battle โหลดสำเร็จ (เช็คปุ่ม AUTO)
   ├── ลูปตรวจสอบทุก 3.5 วินาที:
   │    ├── ถ้า AUTO เป็นสีฟ้า (ปิดอยู่) ──▶ กดเปิด AUTO
   │    ├── ถ้าเป็นปุ่ม "ต่อไป" ──▶ ไม่กด ปล่อยให้เกมนับถอยหลัง 5 วิเอง
   │    └── ถ้าเจอปุ่ม "กลับ" สีทอง (2 เฟรมติด) ──▶ กด 'กลับ' จบแมตช์
   └── Watchdog: ถ้าแมตช์เกิน 16 นาที จะตัดเข้า Emergency Exit กลับสู่ Lobby
   │
   ▼
[State 5: Return to Lobby] ────▶ วนกลับไปเริ่ม State 1 ทำรอบใหม่
```

---

## 5. แนวทางการพัฒนาต่อยอด พร้อมตัวอย่างโค้ด

หากต้องการนำโปรเจกต์นี้ไปพัฒนาต่อ สามารถหยิบโค้ดตัวอย่างด้านล่างไปใส่ใน [bot.py](file:///c:/MonsterBot/bot.py) ได้ทันที:

### 5.1 ระบบแจ้งเตือน Discord Webhook

ใช้สำหรับส่งข้อความสรุปผล หรือส่งภาพแคปหน้าจอเมื่อบอทติด Error เข้าแชแนล Discord ส่วนตัว โดยไม่ต้องลง library ภายนอกเพิ่ม (ใช้ `urllib` ของ Python ได้เลย) หรือใช้ `requests`:

```python
import json
import urllib.request
import os

DISCORD_WEBHOOK_URL = "https://discord.com/api/webhooks/YOUR/WEBHOOK/URL"

def send_discord_message(content):
    """ส่งข้อความแจ้งเตือนธรรมดาเข้า Discord"""
    if not DISCORD_WEBHOOK_URL or "YOUR/WEBHOOK" in DISCORD_WEBHOOK_URL:
        return
    try:
        data = json.dumps({"content": content}).encode("utf-8")
        req = urllib.request.Request(
            DISCORD_WEBHOOK_URL,
            data=data,
            headers={"Content-Type": "application/json", "User-Agent": "MonsterBot"}
        )
        urllib.request.urlopen(req, timeout=5)
    except Exception as e:
        print(f"[Discord Error] {e}")

def send_discord_image(filepath, caption=""):
    """ส่งภาพแคปหน้าจอเข้า Discord (แนะนำติดตั้ง pip install requests)"""
    try:
        import requests
        with open(filepath, "rb") as f:
            requests.post(
                DISCORD_WEBHOOK_URL,
                data={"content": caption},
                files={"file": (os.path.basename(filepath), f, "image/png")},
                timeout=10
            )
    except Exception as e:
        print(f"[Discord Image Error] {e}")
```

**จุดที่นำไปแทรกใน `bot.py`**:
- ในลูป `MATCH COMPLETE`: ส่งสรุปเวลารอบนั้น เช่น `send_discord_message(f"✅ Match #{match_count} จบแล้ว! ใช้เวลา {elapsed_match//60}m {elapsed_match%60}s")`
- ใน `except Exception as e`: เมื่อเกิด Error ให้เรียก `send_discord_image(screenshot_path, f"❌ Bot Error: {e}")`

---

### 5.2 ระบบ Auto-Recovery เปิดเกมใหม่อัตโนมัติเมื่อเกมหลุด

หากปล่อยบอททิ้งไว้นานๆ แล้วเกมแครชหลุดกลับไปหน้าโฮมของ MuMuPlayer สามารถใช้ ADB สั่งตรวจสอบและเปิดเกมขึ้นมาใหม่ได้:

```python
# แทนที่ด้วย Package Name จริงของเกม Monster Saga
# หาชื่อแพ็กเกจได้โดยพิมพ์คำสั่ง: adb shell dumpsys window | grep -E "mCurrentFocus"
GAME_PACKAGE = "com.monster.saga" 

def is_game_running():
    """ตรวจสอบว่าแอปเกมยังรันอยู่หรือไม่"""
    try:
        res = subprocess.run(
            [ADB, "-s", DEVICE, "shell", "pidof", GAME_PACKAGE],
            capture_output=True,
            text=True,
            timeout=5
        )
        return bool(res.stdout.strip())
    except Exception:
        return False

def restart_game():
    """สั่งเปิดเกมขึ้นมาใหม่"""
    print("[RECOVERY] Relaunching game...")
    # สั่งเปิดแอปผ่าน monkey command
    subprocess.run([ADB, "-s", DEVICE, "shell", "monkey", "-p", GAME_PACKAGE, "-c", "android.intent.category.LAUNCHER", "1"])
    time.sleep(15)  # รอเกมโหลดหน้าไตเติ้ล
```

---

### 5.3 ระบบบันทึกสถิติการฟาร์มลงไฟล์ CSV

บันทึกประวัติการเล่นลงไฟล์ `stats.csv` เพื่อนำไปเปิดดูใน Excel หรือสรุปสถิติ:

```python
import csv
from datetime import datetime

STATS_FILE = r"C:\MonsterBot\stats.csv"

def log_match_stats(match_id, duration_seconds, status="SUCCESS"):
    """บันทึกข้อมูลแมตช์ลง CSV"""
    file_exists = os.path.exists(STATS_FILE)
    with open(STATS_FILE, mode="a", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        if not file_exists:
            writer.writerow(["Timestamp", "MatchID", "DurationSec", "DurationFormatted", "Status"])
        
        minutes = duration_seconds // 60
        seconds = duration_seconds % 60
        writer.writerow([
            datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            match_id,
            duration_seconds,
            f"{minutes}m {seconds}s",
            status
        ])
```

---

### 5.4 ระบบปุ่มลัดคีย์บอร์ด (Hotkeys)

หากต้องการหยุดพัก (Pause) หรือหยุดทำงาน (Stop) โดยไม่ต้องสลับจอไปกด `Ctrl + C`:

```bash
pip install keyboard
```

```python
import keyboard
import threading

is_paused = False
is_running = True

def hotkey_listener():
    global is_paused, is_running
    while is_running:
        if keyboard.is_pressed("f8"):
            is_paused = not is_paused
            state_str = "PAUSED (กด F8 อีกครั้งเพื่อเล่นต่อ)" if is_paused else "RESUMED"
            print(f"\n>>> [HOTKEY F8] บอทสถานะ: {state_str} <<<\n")
            time.sleep(0.5)
        elif keyboard.is_pressed("f9"):
            print("\n>>> [HOTKEY F9] กำลังหยุดการทำงานของบอท... <<<\n")
            is_running = False
            break
        time.sleep(0.1)

# เริ่มฟังเสียงปุ่มใน Background Thread ก่อนเข้าลูปหลัก
threading.Thread(target=hotkey_listener, daemon=True).start()

# ในลูปหลักของบอท:
# while is_running:
#     if is_paused:
#         time.sleep(1)
#         continue
```

---

### 5.5 การแยกคอนฟิกออกเป็น config.json

เพื่อความสะดวกในการปรับแต่งพิกัดและค่า Timeout โดยไม่ต้องแก้โค้ด Python สามารถแยกเป็นไฟล์ `config.json`:

```json
{
  "adb_path": "C:\\Program Files\\Netease\\MuMuPlayer\\nx_main\\adb.exe",
  "device": "127.0.0.1:5559",
  "match_timeout": 130,
  "battle_timeout": 330,
  "match_max_timeout": 960,
  "check_interval": 3.5
}
```

---

## 6. วิธีรัน การทดสอบ และการแก้ปัญหาทั่วไป

### 6.1 วิธีเริ่มต้นรันบอท
1. เปิด **MuMuPlayer** แล้วเปิดเกมเข้าสู่หน้า **Lobby**
2. เปิด PowerShell หรือ Command Prompt ไปที่โฟลเดอร์โปรเจกต์:
   ```powershell
   cd C:\MonsterBot
   python bot.py
   ```

### 6.2 การทดสอบระบบก่อนเริ่มรันจริง
- **ทดสอบแคปภาพหน้าจอ**:
  ```powershell
  python screenshot.py
  ```

### 6.3 ปัญหาที่พบบ่อยและการแก้ไข (Troubleshooting)

1. **Error: Device is not connected or emulator is not running**
   - สาเหตุ: พอร์ต ADB ของ MuMuPlayer เปลี่ยน หรือยังไม่ได้เปิดโปรแกรม
   - แก้ไข: รันคำสั่ง `& "C:\Program Files\Netease\MuMuPlayer\nx_main\adb.exe" connect 127.0.0.1:5559` หรือตรวจสอบพอร์ตใน Settings ของ MuMuPlayer

2. **Template Matching ไม่เจอปุ่ม (Confidence ต่ำกว่า Threshold)**
   - สาเหตุ: ขนาดหน้าจอของอีมูเลเตอร์เพี้ยน ไม่ใช่ 1280x720 หรือปุ่มในเกมมีการเปลี่ยนสกิน/กราฟิก
   - แก้ไข: รัน `python screenshot.py` เพื่อแคปภาพปัจจุบัน จากนั้นตรวจสอบตำแหน่งรูปใน `templates/`

3. **บอทไม่ยอมกด AUTO ในระหว่างต่อสู้**
   - สาเหตุ: สีหรือแสงของฉากหลังรอบปุ่ม AUTO มีการเปลี่ยนแปลง
   - แก้ไข: ดูค่า Log `Blue` และ `Yellow` ใน Console จากนั้นปรับค่า `AUTO_BLUE_THRESHOLD` หรือ `AUTO_YELLOW_THRESHOLD` ใน [champ_bot.py](file:///c:/MonsterBot/champ_bot.py) ให้เหมาะสม

---

## 7. โหมดทาวเวอร์ต่อสู้ (Battle Tower - Daily Mode)

โหมด **"ทาวเวอร์ต่อสู้"** ถูกพัฒนาขึ้นในไฟล์ [tower_bot.py](file:///c:/MonsterBot/tower_bot.py) สำหรับการลงหอคอยประจำวันแบบอัตโนมัติ โดยมีระบบจำกัดการเล่นวันละ 1 ครั้ง (`tower_daily_done.txt`)

### 7.1 พิกัดและขั้นตอนสำคัญที่ผ่านการทดสอบจริง (Verified on 1280x720)

| ประเภทชั้น / อีเวนต์ | ปุ่ม / ตำแหน่ง | พิกัด (X, Y) | หมายเหตุสำคัญ |
| :--- | :--- | :--- | :--- |
| **ชั้นคู่ต่อสู้** | ตัวละครคู่แข่ง | `(707, 520)` | ตัวละครที่ลูกศรสีส้ม `⬇️` ชี้อยู่ |
| | ปุ่มท้าทาย (ยาก - สีม่วง) | `(988, 471)` | เลือกระดับยากเพื่อแต้มและเหรียญสูงสุด |
| | ปุ่มต่อสู้ออโต้ | `(52, 255)` | ปุ่มวงกลม "ต่อสู้ออโต้" ทางซ้ายจอ |
| | ปุ่ม "ต่อไป" (หน้าชนะ) | `(800, 630)` | **สำคัญมาก**: โหมดนี้มีบั๊ก เวลานับถอยหลัง 5 วินาทีจะไม่ข้ามให้ ต้องกดปุ่มนี้เสมอ |
| **ชั้นแท่นบัฟ (BUFF)** | สัญลักษณ์โปเกบอล | `(706, 586)` | แตะที่แท่นบัฟเพื่อเปิดหน้าต่าง "ซื้อbuff" |
| | ปุ่มซื้อบัฟโจมตี (ขวาสุด) | `(940, 540)` | ซื้อบัฟ Atk +15% (ราคา 15 เหรียญ) |
| | ปุ่มปิดหน้าต่างซื้อบัฟ | `(1230, 43)` | ปุ่มกากบาทสีฟ้ามุมขวาบน |
| | ปุ่ม "ตกลง" ยืนยันปิด | `(717, 411)` | ยืนยันป๊อปอัป "ยังมีbuffไม่ได้ซื้อ จะปิดไหม" |
| **ชั้นหีบสมบัติ (Chest)** | หีบสมบัติทอง | `(707, 600)` | แตะหีบเพื่อเปิดรับของรางวัล |
| | คลิกรับรางวัล | `(500, 660)` | แตะใต้รางวัลเพื่อปิดหน้าต่างรางวัลฟรี |
| | ปุ่ม "ทิ้งไว้" | `(490, 570)` | **สำคัญ**: กึ่งกลางปุ่ม "ทิ้งไว้" เพื่อปิดหน้าต่าง โดยไม่เสีย 20 เพชร |

### 7.2 วิธีรันบอทโหมดทาวเวอร์
```powershell
cd C:\MonsterBot
python tower_bot.py
```
- บอทจะเริ่มไต่หอคอยตั้งแต่ชั้นที่อยู่ปัจจุบัน (เช่น ชั้น 65) ไปจนถึงชั้น 80
- ใช้ Flow การทำงานเดิมแบบแรกทั้งหมด (คู่ต่อสู้, ซื้อบัฟ, เปิดกล่อง)
- เมื่อเก็บกล่องสุดท้ายที่ชั้น 80 เสร็จสิ้น บอทจะหยุดการทำงานของสคริปต์ทันที (Stop Script) ไม่วนลูปซ้ำ
- บอทจะเช็คว่าวันนี้เล่นไปหรือยัง หากเล่นไปแล้วจะหยุดทำงานทันทีเพื่อป้องกันการลงซ้ำ (รีเซ็ตทุก 05:00 น.)
- หากต้องการบังคับรันใหม่ ให้ลบไฟล์ `C:\MonsterBot\tower_daily_done.txt`


---

## 8. โหมดทาวเวอร์ท้าทาย (Tower Hard Mode - tower_hard_bot.py)

โหมด **"ทาวเวอร์ท้าทาย (Hard Mode)"** ในไฟล์ [tower_hard_bot.py](file:///c:/MonsterBot/tower_hard_bot.py) ได้รับการออกแบบให้สามารถกดรันได้ทุกเมื่อตามต้องการ:

- **ไม่มีการจำกัดวันละ 1 ครั้ง**: สามารถสั่ง `python tower_hard_bot.py` ได้ตลอดเวลา ไม่มีการล็อกไฟล์ txt หากต้องการหยุดหรือรันใหม่สามารถทำได้ทันทีโดยไม่ต้องมาคอยลบไฟล์
- **การหยุดทำงาน**: บอทจะหยุดทำงานโดยอัตโนมัติเฉพาะเมื่อตรวจพบว่าถึง **ชั้น 80** และเปิดกล่องสมบัติใบสุดท้ายเสร็จสิ้นแล้วเท่านั้น (ระบบแสดงข้อความเกม `ถึงชั้นสูงสุดแล้ว!`)
- **โครงสร้างการไต่หอคอย Hard Mode**:
  - ลิฟต์เลื่อนข้ามชั้นทีละ 5 ชั้น (`... -> 65 -> 70 -> 75 -> 80`)
  - ในแต่ละช่วงชั้นจะมี 5 Step ประกอบด้วย:
    1. **การต่อสู้ส่วนบุคคล (Personal Battle)**: ศัตรู 1 Wave ปุ่มท้าทายอยู่ที่ `(638, 410)`
    2. **แท่นซื้อบัฟ (Buff Station)**: สัญลักษณ์โปเกบอล `(706, 586)` ซื้อบัฟ Atk/Def จนเหรียญหมด ข้ามฮีล ยืนยันปิดหน้าต่าง
    3. **การต่อสู้ส่วนบุคคล (Personal Battle)**: รอบที่สอง
    4. **กล่องสมบัติ (Chest)**: กล่องทอง `(707, 600)` กดรับรางวัลฟรี และกด "ทิ้งไว้" `(430, 575)` ป้องกันการเสียเพชร
    5. **การต่อสู้ทีม (Team Battle 3v3)**: ศัตรู 3 Wave ต่อเนื่อง เลือดรวมหลักสิบล้าน (เช่น Ho-Oh/Xerneas) บอทมอนิเตอร์การต่อสู้ยาวนานถึง 600 วินาที พร้อมกด "ต่อไป" `(800, 630)` เมื่อจบแต่ละ Wave
- **ผลการทดสอบจริง (Verified Cleared to Floor 80)**:
  - ผ่านการต่อสู้ครบทุกแมตช์จริง ไม่มีการหลุดหรือ False Positive
  - ชนะการต่อสู้ทีม 3 Wave สำเร็จ (รับ 680 ไดมอนด์ + 15 เหรียญ)
  - ทำภารกิจประจำวัน `[วัน] หอ PK โหมดต่อสู้ (เสร็จสิ้น)` ครบถ้วน
  - ไต่ถึงชั้น 80 เต็มแม็กซ์ สะสมคะแนนวันนั้นได้ 14,300 แต้ม บัฟเต็มทุกแถว และเก็บหีบสมบัติชั้น 80 สำเร็จ

---

## 9. โหมดเขตลับและรวมเลเวลอัตโนมัติ (Secret Realm Auto Farm & Fusion Loop - secret_realm_bot.py)

โหมด **"ฟาร์มเขตลับและรวมเลเวลอัตโนมัติ (Secret Realm Full Loop)"** พัฒนาขึ้นในไฟล์ [secret_realm_bot.py](file:///c:/MonsterBot/secret_realm_bot.py) เพื่อให้บอททำงานวนลูปฟาร์มจับโปเกมอนและย่อยเลเวลแบบอัตโนมัติสมบูรณ์ 24/7

### 9.1 โครงสร้าง 3 Phases
1. **Phase 1 (ฟาร์มจับโปเกมอน):**
   - วนกด "จับอีกครั้ง" (`catch_again_button.png` / `(752, 559)`)
   - ดักจับ Popup กระเป๋าเต็ม 120/120 (`dialog_ok_button.png` / `(647, 419)`)
   - กดยืนยัน ปิดหน้าต่าง และถอยกลับสู่ Lobby อย่างสมบูรณ์
2. **Phase 2 (รวมเลเวล & เคลียร์กระเป๋า):**
   - เข้าหน้า "โปเกมอน" `(1150, 660)` เลือกตัวหลัก Slot 5 `(1100, 280)` (W.Kyurem)
   - แตะแท็บ "ฝึก" `(1230, 487)`
   - วนรวมโปเกมอน 12 ช่องพร้อมกัน โดยมีตัวตรวจสอบ `guardian_pet_text.png` ป้องกันการรวมการ์เดียนเพท
3. **Phase 3 (เดินทางกลับเข้าเขตลับ โซนธรรมดา):**
   - จาก Lobby กดปุ่ม "ฝึก" `(1170, 70)` และแท็บ "ผจญภัย" `(80, 380)`
   - เลื่อนหน้าจอ (Swipe: `500, 580 -> 500, 200`) ค้นหาการ์ด "เขตลับโปเกมอน"
   - แตะปุ่มสีทอง "เข้าร่วม" บนการ์ดที่คำนวณตำแหน่งจริง
   - ตรวจจับโซน: หากอยู่โซนสูง กดสลับไป "โซนธรรมดา" `(1120, 410)`
   - แตะเปิดแถบข้าวหลามตัด "การจับอัตโนมัติ" (`auto_catch_diamond.png` / `(875, 655)`)
   - แตะปุ่ม "เริ่มจับ" (`start_catch_button.png` / `(835, 680)`)

### 9.2 ระบบความปลอดภัยและความเสถียร (Circuit Breaker & Safety Gate)
- **Lobby Verification:** ตรวจสอบหน้า Lobby ด้วย `lobby_train_btn_v2.png` และ `main_lobby_plus_btn.png` (Threshold 0.78) ป้องกันการสับสนระหว่างปุ่มกากบาท [X] กับปุ่มผจญภัยมุมขวาบน
- **Safety Gate:** ตรวจสอบยืนยันหน้าจอหลังกดเข้าร่วมเขตลับ หากหลุดเข้าโหมดอื่นหรือไม่พบองค์ประกอบของเขตลับ จะสั่งกด `[X]` ถอนตัวกลับ Lobby ทันที
- **Loop Lock:** บล็อก Master Loop ไม่ให้เริ่ม Phase 1 ตราบใดที่ยังเข้าสู่เขตลับไม่สำเร็จ 100% ป้องกันการเผลอกดปุ่ม "ถ่ายทอด" บนหน้า Lobby
- **Phase 1 Timeout:** หากไม่พบปุ่มควบคุมการจับนานเกิน 8-15 วินาที ระบบจะกด [X] ย้อนกลับ Lobby และเริ่มการนำทางใหม่ทันที ไม่มีการติดลูปค้าง

---
*เอกสารนี้จัดทำและอัปเดตล่าสุดเมื่อ: 2026-10-03 สำหรับ MonsterBot Project (Verified Secret Realm Full Loop 40+ Mins Stable)*

