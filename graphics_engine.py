"""
graphics_engine.py - Advanced Computer Graphics & Visual Overlay Engine
========================================================================
Implements graphics rendering matching user reference UI specs:
  1. Bright Cyan Track Polygon Outline (#00FFFF)
  2. Red Bounding Frames + Floating Labels + Anchor Dot
  3. Prominent Top-Left Alert Banner ("ALERT: Person on track!")
  4. Kalman Trajectory Prediction Vectors
  5. Accumulating Motion/Intrusion Heatmap Layer
========================================================================
"""

import time
import cv2
import numpy as np
from detection_engine import Detection

class GraphicsEngine:
    def __init__(self, width: int = 1280, height: int = 720):
        self.width = width
        self.height = height
        # Heatmap accumulator (float32 single channel)
        self.heatmap_accumulator = np.zeros((height, width), dtype=np.float32)

    def resize(self, width: int, height: int):
        if self.width != width or self.height != height:
            self.width = width
            self.height = height
            self.heatmap_accumulator = np.zeros((height, width), dtype=np.float32)

    # ── 1. Track Polygon (Cyan ROI) ──────────────────────────
    def draw_track_polygon(self, frame: np.ndarray, polygon: np.ndarray) -> np.ndarray:
        """
        Draw clean, bright cyan track boundary line (#00FFFF -> BGR: (255, 255, 0))
        and light alpha fill.
        """
        if polygon is None or len(polygon) < 3:
            return frame

        # Light cyan transparent fill
        overlay = frame.copy()
        cv2.fillPoly(overlay, [polygon], (255, 255, 0))
        cv2.addWeighted(overlay, 0.12, frame, 0.88, 0, dst=frame)

        # Thick cyan boundary line
        cv2.polylines(frame, [polygon], isClosed=True, color=(255, 255, 0), thickness=3, lineType=cv2.LINE_AA)
        return frame

    # ── 2. Reference Match Bounding Box & Anchor Dot ──────────
    def draw_detection_box(self, frame: np.ndarray, det: Detection) -> np.ndarray:
        """
        Renders bounding box matching reference image:
          - Solid red bounding box
          - Text label above: "Class Conf" (e.g. Person 0.43)
          - Red filled circle dot at bottom center anchor point
        """
        x1, y1, x2, y2 = det.bbox
        color = (0, 0, 255) if det.is_critical or det.zone == "HAZARD" else (0, 255, 0)
        
        # Draw bounding rectangle
        cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2, cv2.LINE_AA)

        # Draw red anchor dot at bottom center
        cv2.circle(frame, det.anchor, 5, (0, 0, 255), -1, cv2.LINE_AA)

        # Label floating above box
        label_text = f"{det.class_name.title()} {det.confidence:.2f}"
        if det.distance_m > 0:
            label_text += f" ({det.distance_m:.1f}m)"

        cv2.putText(
            frame, 
            label_text, 
            (x1, max(y1 - 8, 20)), 
            cv2.FONT_HERSHEY_SIMPLEX, 
            0.6, 
            color, 
            2, 
            cv2.LINE_AA
        )

        return frame

    # ── 3. Top-Left Bold Alert Text ──────────────────────────
    def draw_alert_banner(self, frame: np.ndarray, hazards: list[Detection]) -> np.ndarray:
        """
        Renders prominent red alert text at top left matching reference image:
        "ALERT: Person on track!"
        """
        if not hazards:
            return frame

        # Find highest priority hazard in track
        critical_hazard = hazards[0]
        hazard_label = critical_hazard.class_name.title()
        
        if critical_hazard.zone == "HAZARD":
            alert_text = f"ALERT: {hazard_label} on track!"
        elif critical_hazard.is_critical:
            alert_text = f"WARNING: {hazard_label} approaching track (TTC: {critical_hazard.ttc_sec}s)!"
        else:
            return frame

        # Red text with shadow for maximum contrast
        cv2.putText(frame, alert_text, (25, 45), cv2.FONT_HERSHEY_SIMPLEX, 1.1, (0, 0, 0), 5, cv2.LINE_AA)
        cv2.putText(frame, alert_text, (25, 45), cv2.FONT_HERSHEY_SIMPLEX, 1.1, (0, 0, 255), 2, cv2.LINE_AA)
        
        return frame

    # ── 4. Trajectory Vector ─────────────────────────────────
    def draw_trajectory(self, frame: np.ndarray, det: Detection) -> np.ndarray:
        """Draw trajectory prediction line from center to predicted future location."""
        if det.track_id != -1 and det.predicted_future_pt != det.center:
            cv2.line(frame, det.center, det.predicted_future_pt, (255, 0, 255), 2, cv2.LINE_AA)
            cv2.circle(frame, det.predicted_future_pt, 4, (255, 0, 255), -1, cv2.LINE_AA)
        return frame

    # ── 5. Accumulating Intrusion Heatmap ─────────────────────
    def update_and_draw_heatmap(self, frame: np.ndarray, detections: list[Detection], enabled: bool = True) -> np.ndarray:
        """Accumulate hazard centroids into a floating-point heatmap and composite it."""
        h, w = frame.shape[:2]
        self.resize(w, h)

        if enabled:
            # Decay existing heat over time
            self.heatmap_accumulator *= 0.96

            # Add heat for current detections
            for det in detections:
                if det.zone == "HAZARD" or det.is_critical:
                    cx, cy = det.anchor
                    cv2.circle(self.heatmap_accumulator, (cx, cy), 25, 1.0, -1)

            # Normalize & apply COLORMAP_JET
            norm_heat = cv2.normalize(self.heatmap_accumulator, None, 0, 255, cv2.NORM_MINMAX)
            heat_uint8 = np.uint8(norm_heat)
            color_heatmap = cv2.applyColorMap(heat_uint8, cv2.COLORMAP_JET)

            # Mask only hot areas and blend
            mask = heat_uint8 > 20
            overlay = frame.copy()
            overlay[mask] = cv2.addWeighted(frame[mask], 0.4, color_heatmap[mask], 0.6, 0)
            return overlay

        return frame


def render_pipeline(
    frame: np.ndarray, 
    detections: list[Detection], 
    track_polygon: np.ndarray, 
    graphics_engine: GraphicsEngine,
    show_heatmap: bool = False,
    show_trajectory: bool = True
) -> np.ndarray:
    """Master compositing pipeline."""
    # 1. Heatmap layer
    frame = graphics_engine.update_and_draw_heatmap(frame, detections, enabled=show_heatmap)
    
    # 2. Cyan Track Polygon
    frame = graphics_engine.draw_track_polygon(frame, track_polygon)

    # 3. Bounding Boxes & Trajectories
    hazards_in_zone = []
    for det in detections:
        frame = graphics_engine.draw_detection_box(frame, det)
        if show_trajectory:
            frame = graphics_engine.draw_trajectory(frame, det)
        
        if det.is_critical or det.zone == "HAZARD":
            hazards_in_zone.append(det)

    # 4. Top-Left Bold Red Alert Text (Reference match)
    frame = graphics_engine.draw_alert_banner(frame, hazards_in_zone)

    return frame
