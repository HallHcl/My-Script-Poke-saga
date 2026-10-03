# MonsterBot Development Rules & Agent Guidelines

## กฎเหล็ก: Anti-Loop & Fast Communication (ป้องกันการติดลูปและจำกัดการกระทำซ้ำ)
ห้ามทำ Sub-actions ซ้ำไปซ้ำมาในเบื้องหลังจนผู้ใช้ต้องรอนาน โดยต้องปฏิบัติตามข้อตกลงอย่างเคร่งครัด:

1. **กฎ 2-Action Stop (จำกัดการตรวจสอบต่อเทิร์น):**
   - ในแต่ละเทิร์น แคปภาพหรือรันคำสั่งตรวจสอบสถานะได้**ไม่เกิน 2 ครั้ง**
   - ห้ามรันลูปย่อยเงียบๆ ติดต่อกันเกินจำเป็น (เช่น แคป -> ครอป -> คำนวณ -> แคปซ้ำ -> เทสต์คลิก) ภายในเทิร์นเดียว
2. **เจอ RCA หรือปัญหา ต้องหยุดรายงานทันที:**
   - เมื่อตรวจพบสาเหตุ (Root Cause Analysis - RCA) หรือพฤติกรรมหน้าจอไม่เป็นไปตามคาด **ต้องหยุดเรียก Tool ทันที** แล้วตอบผู้ใช้ด้วยข้อความสั้นกระชับ:
     - ปัญหา/สาเหตุที่พบ (RCA) คืออะไร
     - ภาพหน้าจอปัจจุบันแสดงอะไร
     - เสนอทางเลือกหรือวิธีแก้ไข 1-2 ข้อ
3. **ถามก่อนเดา (Ask Before Guessing):**
   - หากหน้าจอมีสถานะไม่แน่นอน หรือมีตัวเลือกหลายทาง ให้ถามผู้ใช้ทันที ห้ามตั้งสมมติฐานแล้วทดลองคลิกสุ่มเองในความมืด
4. **สรุปความคืบหน้าแบบกระชับ:**
   - รายงานเฉพาะสิ่งสำคัญและ Action ถัดไป ไม่เวิ่นเว้อ

## กฎเหล็ก: ทำความเข้าใจ Game Flow ที่แท้จริงก่อนลงมือทำ (Prerequisite: Real Game Flow Discovery)
ก่อนที่จะเริ่มเขียนโค้ด, แก้ไขลูป, หรือเพิ่ม Task/ฟีเจอร์ใหม่สำหรับบอท **ต้องทำขั้นตอนสำรวจและตรวจสอบ Game Flow จริงให้ครบถ้วนก่อนเสมอ** ห้ามเดาพิกัด ห้ามสมมติหน้าจอ และห้ามเขียนโค้ดข้ามขั้นตอนเด็ดขาด โดยต้องทำตาม 5 ขั้นตอนนี้ให้ครบ:

### 1. Screen & Asset Inventory (เก็บภาพหน้าจอจริงทุกสถานะ)
- ใช้ `screenshot.py` แคปภาพหน้าจอจริงของทุก State ที่เกี่ยวข้อง เช่น หน้าเริ่มต้น, กำลังโหลด, หน้าเตรียมทีม, หน้าต่อสู้จริง, หน้าชนะ/แพ้, หน้าป๊อปอัปผลรางวัล, และหน้า Lobby
- หาพิกัด (X, Y) และสี (RGB/HSV) จากภาพจริงเท่านั้น (Native Resolution: 1280x720)
- สร้างและตรวจสอบไฟล์ Template ให้อยู่ใน [templates/](file:///c:/Users/kchan/MonsterBot/templates/)

### 2. State & Transition Mapping (ทำผังการไหลและการแยกสาย)
- กำหนด State Machine ชัดเจน (Happy Path) ตั้งแต่จุดเริ่มต้นจนจบลูป
- บันทึกเงื่อนไข Trigger และการหน่วงเวลา (Delays / Animations) เช่น การรอลิฟต์หยุดนิ่ง, ประตูเปิด, หรือการโหลดฉาก เพื่อไม่ให้กดก่อนที่หน้าจอจะพร้อม

### 3. Interruption & Edge Cases Discovery (สำรวจเหตุการณ์แทรกแซง)
- ดักจับหน้าต่างป๊อปอัปที่ไม่คาดคิด: กล่องสมบัติ, ร้านค้าบัฟ, แจ้งเตือนสตามิน่าหมด, แจ้งเตือนเน็ตหลุด, หรือป๊อปอัปเควสต์
- ต้องมี Fallback / Escape Sequence ที่การันตีว่าสามารถพากลับสู่ Lobby ได้อย่างปลอดภัย 100%

### 4. Stability & Multi-frame Debounce (ตรวจความนิ่งของสถานะ)
- ต้องเช็คให้มั่นใจว่าหน้าจอนิ่งจริง (Static Check) ก่อนแตะหน้าจอ เพื่อไม่ให้แตะโดนตำแหน่งอื่นระหว่างเคลื่อนไหว
- ใช้ Multi-frame Debouncing (ต้องตรงเงื่อนไข 2-3 เฟรมติดต่อกัน) ป้องกัน False Positive จากเอฟเฟกต์สกิล

### 5. Step-by-Step Verification Walkthrough (ทดสอบทีละสเต็ปก่อนรันจริง)
- ทดสอบ Action ทีละก้าวแบบ Step-by-step โดยแคปภาพตรวจสอบผลลัพธ์หลังแตะทุกครั้ง
- ยืนยันว่าจบลูปแล้ว บอทสามารถเริ่มรอบถัดไปได้อย่างเสถียร ไม่ติดลูปตาย

---

## เอกสารอ้างอิงและทักษะในโปรเจกต์
- [game-state-orchestrator](.agents/skills/game-state-orchestrator/SKILL.md): สถาปัตยกรรม State Machine, Circuit Breaker, Navigation Graph
- [adb-game-controller](.agents/skills/adb-game-controller/SKILL.md): ควบคุม ADB, จำลอง Touch แบบมนุษย์, Process Recovery
- [game-computer-vision](.agents/skills/game-computer-vision/SKILL.md): OpenCV Template Matching, HSV Masking, Debounce
- [game-bot-monitoring](.agents/skills/game-bot-monitoring/SKILL.md): Discord Alerts, Error Screenshot, CSV Stats
- [HANDOVER.md](HANDOVER.md): รายละเอียดพิกัด, Threshold, และประวัติการพัฒนาระบบ
