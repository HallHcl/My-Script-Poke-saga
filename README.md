# My-Script-Poke-saga (MonsterBot)

ระบบบอทอัตโนมัติสำหรับเกม Pokemon Saga / Monster Saga บน Android Emulator (MuMuPlayer) ผ่าน ADB และ OpenCV Computer Vision

## ฟังก์ชันการทำงานหลัก (Core Features)

1. **Pokemon Saga (`bots/pokemon_saga/`)**:
   - **Secret Realm & Fusion Farm (`bots/pokemon_saga/secret_realm_bot.py`)**:
     - ลูปอัตโนมัติเต็มรูปแบบ: ล็อบบี้ ➔ เข้าเขตลับ (Pokemon Secret Realm โซนธรรมดา) ➔ กดจับอัตโนมัติจนกระเป๋าเต็ม (120/120)
     - วาร์ปกลับล็อบบี้ ➔ เข้าเมนูโปเกมอน ➔ รวมเลเวลตัวหลัก (W.Kyurem) โดยเลือกทีละ 12 ช่องรวดเร็ว
     - ระบบหยุดอัตโนมัติเมื่อเจอกลุ่ม "การ์เดียนเพท" (Guardian Pet) ป้องกันการนำโปเกมอนสำคัญไปรวม
     - ทำงานวนซ้ำตลอด 24 ชม. พร้อม Circuit Breaker กู้คืนสถานะกลับสู่หน้าล็อบบี้หากเกิดเหตุขัดข้อง

2. **Monster Saga (`bots/monster_saga/`)**:
   - **Champion League Bots**:
     - `champ_bot.py`: โหมด 3 Wave (เลือก 3-3-3 ตัว, Auto ทุก Wave)
     - `champ_bot_season2.py`: โหมด 3 Wave (เลือก 1-2-3 ตัว, Wave 1 Manual + กดสกิล, Wave 2-3 Auto)
   - **Extreme Tower Auto-Climber**:
     - `tower_bot.py`: ไต่หอคอยโหมดปกติ 80 ชั้น
     - `tower_hard_bot.py`: ไต่หอคอยโหมดท้าทาย (Hard) ซื้อบัฟตาม Priority สู้ทีมหลาย Wave จบชั้น 80

## ข้อกำหนดระบบ (Requirements)

- **Emulator**: MuMuPlayer (หรือโปรแกรมจำลอง Android อื่นๆ)
- **Native Resolution**: 1280 x 720 (DPI 240)
- **Python**: 3.8+
- **การเชื่อมต่อ**: ADB (Android Debug Bridge) เชื่อมต่อพอร์ตจำลอง (เช่น `127.0.0.1:5559` หรือ `127.0.0.1:16384`)

## การติดตั้งและการเริ่มใช้งาน (Setup & Usage)

1. ติดตั้ง Dependencies ที่จำเป็น:
   ```bash
   pip install -r requirements.txt
   ```
2. เชื่อมต่อ ADB ไปยัง Emulator:
   ```bash
   adb connect 127.0.0.1:5559
   ```
3. คำสั่งเริ่มต้นรันบอทแต่ละโหมด:
   - **Pokemon Saga (เขตลับ + รวมเลเวล):**
     ```bash
     python bots/pokemon_saga/secret_realm_bot.py
     # หรือรันผ่าน root launcher:
     python secret_realm_bot.py
     ```
   - **Monster Saga (แชมเปี้ยนลีก Season 2):**
     ```bash
     python bots/monster_saga/champ_bot_season2.py
     ```
   - **Monster Saga (ไต่หอคอย Hard):**
     ```bash
     python bots/monster_saga/tower_hard_bot.py
     ```
