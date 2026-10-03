---
name: game-computer-vision
description: >-
  Techniques for game automation computer vision using OpenCV, HSV color thresholding,
  template matching, multi-frame debouncing, and digit extraction.
---

# Game Computer Vision Skill

## 1. HSV Color Space Detection
RGB/BGR is vulnerable to game lighting, shadows, and screen alpha blends. Always convert to HSV (`cv2.cvtColor(img, cv2.COLOR_BGR2HSV)`) for color-based triggers.

### Established Project Presets:
- **Blue AUTO Button (OFF)**:
  - Lower: `[85, 100, 100]`, Upper: `[130, 255, 255]`
  - Threshold: `AUTO_BLUE_THRESHOLD = 0.25`
- **Yellow/Gold AUTO Button (ON)**:
  - Lower: `[20, 120, 120]`, Upper: `[38, 255, 255]`
  - Threshold: `AUTO_YELLOW_THRESHOLD = 0.08`
- **Gold/Orange Result Buttons**:
  - Lower: `[12, 100, 140]`, Upper: `[28, 255, 255]`

## 2. Template Matching Best Practices
```python
res = cv2.matchTemplate(screenshot, template, cv2.TM_CCOEFF_NORMED)
min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(res)
if max_val >= threshold:
    h, w = template.shape[:2]
    center_x = max_loc[0] + w // 2
    center_y = max_loc[1] + h // 2
```

### Multi-frame Debounce (Consecutive Frames)
To avoid false positives during screen transitions, animations, or VFX:
- Require finding the template for at least `N = 2` consecutive frames (`REQUIRED_CONSECUTIVE_FRAMES = 2`).

## 3. Digit Extraction via HSV & Masking
When OCR fails due to stylized game fonts:
1. Crop Region of Interest (ROI).
2. Filter color mask (e.g. Yellow numbers).
3. Match individual digit templates (`digit_0.png` through `digit_9.png`).
