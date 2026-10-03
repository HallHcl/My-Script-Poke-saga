---
name: game-state-orchestrator
description: >-
  Architectural patterns for game state machines (HFSM), daily task schedulers,
  universal navigation graphs, circuit breaker watchdogs, and state persistence.
---

# Game State Orchestrator Skill

## 0. Prerequisite: Real Game Flow Discovery Protocol (ข้อกำหนดสำคัญก่อนเริ่มพัฒนา)
> **กฎเหล็ก (Golden Rule)**: ห้ามเริ่มเขียนโค้ดลูปหรือเดา Action ใดๆ เด็ดขาด จนกว่าจะสำรวจและเข้าใจ Game Flow ที่แท้จริงครบทุกขั้นตอน (Ground-Truth Observation)

ก่อนเริ่มสร้างหรือปรับปรุง Task/State ใดๆ ต้องดำเนินการตาม 5 ขั้นตอน (5-Step Discovery) ให้ครบถ้วน:
1. **Screen & Asset Inventory (เก็บภาพและระบุสถานะจริง)**:
   - ใช้ `screenshot.py` แคปภาพหน้าจอจริงของทุกสถานะ: หน้าเริ่มต้น, กำลังโหลด, การเตรียมตัว, การต่อสู้, ผลลัพธ์ (ชนะ/แพ้), ป๊อปอัป และหน้า Lobby
   - ห้ามเดาพิกัดหรือรูปทรงปุ่ม ต้องมีภาพอ้างอิงและวัดพิกัด/สีจริงจากภาพหน้าจอ (Resolution 1280x720)
2. **Transition & Branch Mapping (ทำผังการไหลและการแยกสาย)**:
   - วาดเส้นทาง State Machine (Happy Path) ตั้งแต่ต้นจนจบ
   - ระบุ Trigger และ Guard Conditions: กดจุดไหนแล้วจะไปหน้าไหน, อนิเมชันหรือการโหลดใช้เวลากี่วินาที (เช่น รอลิฟต์หยุดนิ่ง, รอประตูเปิด)
3. **Interruption & Edge Cases Discovery (สำรวจสิ่งที่อาจขัดจังหวะ)**:
   - ตรวจจับหน้าต่างแทรกแซง: กล่องสมบัติ, ร้านค้าบัฟ, แจ้งเตือนสตามิน่าหมด, แจ้งเตือนเน็ตหลุด, ป๊อปอัปเควสต์
   - กำหนด Fallback & Escape Sequence: หากเกิดข้อผิดพลาด ต้องมีขั้นตอนพากลับสู่หน้าปลอดภัย (Lobby) ได้เสมอ
4. **State Stability & Multi-frame Debounce (ตรวจความนิ่งของสถานะ)**:
   - ตรวจสอบว่าหน้าจอนิ่งจริงก่อนสั่งคลิก (ป้องกันการคลิกระหว่าง Fade in, Loading หรือ Transition)
   - ใช้ Multi-frame Debounce (เช่น ตรวจพบ 2-3 เฟรมติดต่อกัน) เพื่อยืนยันว่าถึง State นั้นจริง ไม่ใช่ภาพลวงตาจากสกิลหรือเอฟเฟกต์
5. **End-to-End Manual Trace Walkthrough (ทดสอบลูปแบบทีละก้าว)**:
   - จำลองลูปการทำงานทีละ Action พร้อมแคปหน้าจอตรวจสอบผลลัพธ์จริงจนจบลูป 1 รอบเต็ม
   - ยืนยันว่าจบงานแล้วสามารถพากลับสู่ Lobby หรือจุดเริ่มต้นได้อย่างปลอดภัย 100%

## 1. Universal Navigation Graph
Full-game automation requires moving between any two screens safely:
- Every screen must declare its `breadcrumbs` or `parent_screen`.
- **Return to Lobby Guarantee**: An escape sequence that repeatedly taps back/close buttons until the Lobby screen is confirmed with high template confidence.

```text
[Current Screen] ---> (Taps Esc/Back/X) ---> [Lobby] ---> (Taps Target Button) ---> [Target Mode]
```

## 2. Daily Routine & Priority Queue
Tasks should inherit from a common interface:
```python
class BaseTask:
    name: str
    priority: int
    def can_run(self) -> bool: ...
    def execute(self) -> bool: ...
    def cleanup(self) -> None: ...
```
- Daily claims (Mail, Check-in, Friends) have top priority.
- Limited entry modes (Tower, Daily Dungeon) run next.
- Stamina burning / Endless farming runs during leftover time.

## 3. Circuit Breaker & Watchdogs
Every state in a game loop must have an expiration timer:
- **State Timeout**: If a battle takes > 5m30s, trigger emergency recovery.
- **Match Circuit Breaker**: If an entire 3-wave match takes > 16 minutes, force abort.
- **Deadlock Breaker**: If screen remains unchanged across 5 inspection cycles, trigger recovery.
