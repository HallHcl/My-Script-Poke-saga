import os
import cv2
import numpy as np
from typing import Optional, Tuple, Dict


class Vision:
    """Computer Vision Engine for UI Detection, HSV Color Masking, and Template Matching."""

    def __init__(self, templates_dir: str = "templates"):
        self.templates_dir = templates_dir
        self.template_cache: Dict[str, np.ndarray] = {}

    def load_template(self, filename: str) -> Optional[np.ndarray]:
        """Load template from disk or memory cache."""
        if filename in self.template_cache:
            return self.template_cache[filename]

        path = os.path.join(self.templates_dir, filename) if not os.path.isabs(filename) else filename
        if not os.path.exists(path):
            return None

        tpl = cv2.imread(path, cv2.IMREAD_COLOR)
        if tpl is not None:
            self.template_cache[filename] = tpl
        return tpl

    def match(self, image: np.ndarray, template_name: str, threshold: float = 0.85,
              roi: Optional[Tuple[int, int, int, int]] = None) -> Optional[Tuple[int, int, float]]:
        """
        Search for template inside image (or ROI [x1, y1, x2, y2]).
        Returns (center_x, center_y, confidence) or None.
        """
        tpl = self.load_template(template_name)
        if tpl is None or image is None:
            return None

        search_img = image
        offset_x, offset_y = 0, 0
        if roi:
            x1, y1, x2, y2 = roi
            search_img = image[y1:y2, x1:x2]
            offset_x, offset_y = x1, y1

        th, tw = tpl.shape[:2]
        ih, iw = search_img.shape[:2]
        if ih < th or iw < tw:
            return None

        res = cv2.matchTemplate(search_img, tpl, cv2.TM_CCOEFF_NORMED)
        _, max_val, _, max_loc = cv2.minMaxLoc(res)

        if max_val >= threshold:
            cx = offset_x + max_loc[0] + tw // 2
            cy = offset_y + max_loc[1] + th // 2
            return (cx, cy, float(max_val))

        return None

    def color_ratio(self, image: np.ndarray, roi: Tuple[int, int, int, int],
                    lower_hsv: np.ndarray, upper_hsv: np.ndarray) -> float:
        """Calculate the proportion of pixels matching an HSV color range within ROI."""
        x1, y1, x2, y2 = roi
        crop = image[y1:y2, x1:x2]
        if crop.size == 0:
            return 0.0

        hsv = cv2.cvtColor(crop, cv2.COLOR_BGR2HSV)
        mask = cv2.inRange(hsv, lower_hsv, upper_hsv)
        ratio = float(np.count_nonzero(mask)) / mask.size
        return ratio

    def is_auto_on(self, image: np.ndarray, roi: Tuple[int, int, int, int] = (7, 111, 105, 209)) -> bool:
        """
        Check battle AUTO button status.
        Yellow/Gold = ON, Blue/Cyan = OFF.
        """
        yellow_lower = np.array([20, 120, 120])
        yellow_upper = np.array([38, 255, 255])
        yellow_ratio = self.color_ratio(image, roi, yellow_lower, yellow_upper)
        return yellow_ratio >= 0.08

    def is_auto_off(self, image: np.ndarray, roi: Tuple[int, int, int, int] = (7, 111, 105, 209)) -> bool:
        """Check if AUTO button is currently OFF (Blue)."""
        blue_lower = np.array([85, 100, 100])
        blue_upper = np.array([130, 255, 255])
        blue_ratio = self.color_ratio(image, roi, blue_lower, blue_upper)
        return blue_ratio >= 0.25
