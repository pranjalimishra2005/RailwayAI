"""
detection_engine.py - Advanced YOLOv8 ByteTrack, Kalman Trajectory & TTC Engine
==================================================================================
Computer Graphics & ML Concepts Used:
  - Multi-Object Tracking (MOT) using YOLOv8 ByteTrack
  - Kalman Filter (cv2.KalmanFilter) for 2D position/velocity state estimation
  - Time-to-Collision (TTC) prediction based on ground-plane trajectories
  - Homography / Inverse Perspective Mapping (IPM) for real-world distance (m) and speed (km/h)
==================================================================================
"""

import time
import cv2
import numpy as np
from collections import defaultdict
from ultralytics import YOLO

# ────────────────────────────────────────────────────────────
# Hazard Classification Mapping
# ────────────────────────────────────────────────────────────
HAZARD_CLASSES = {
    "person": "HUMAN",
    "bicycle": "OBSTACLE", "car": "OBSTACLE", "motorcycle": "OBSTACLE",
    "bus": "OBSTACLE", "truck": "OBSTACLE",
    "cat": "ANIMAL", "dog": "ANIMAL", "horse": "ANIMAL",
    "cow": "ANIMAL", "elephant": "ANIMAL", "bear": "ANIMAL",
    "sheep": "ANIMAL", "bird": "ANIMAL",
    "backpack": "DEBRIS", "suitcase": "DEBRIS", "umbrella": "DEBRIS",
    "chair": "OBSTACLE", "bench": "OBSTACLE",
    "train": "TRAIN",
}

HAZARD_PRIORITY = {
    "HUMAN": 0,
    "ANIMAL": 1,
    "OBSTACLE": 2,
    "DEBRIS": 3,
    "TRAIN": 4,
    "UNKNOWN": 5,
}

# ────────────────────────────────────────────────────────────
# Kalman Filter Tracker Wrapper
# ────────────────────────────────────────────────────────────
class ObjectKalmanFilter:
    """
    2D Constant Velocity Kalman Filter:
    State: [x, y, vx, vy]^T
    Measurement: [x, y]^T
    """
    def __init__(self, init_x: float, init_y: float):
        self.kf = cv2.KalmanFilter(4, 2)
        self.kf.measurementMatrix = np.array([[1, 0, 0, 0],
                                              [0, 1, 0, 0]], np.float32)
        self.kf.transitionMatrix = np.array([[1, 0, 1, 0],
                                             [0, 1, 0, 1],
                                             [0, 0, 1, 0],
                                             [0, 0, 0, 1]], np.float32)
        self.kf.processNoiseCov = np.eye(4, dtype=np.float32) * 0.03
        self.kf.measurementNoiseCov = np.eye(2, dtype=np.float32) * 0.5
        self.kf.errorCovPost = np.eye(4, dtype=np.float32)
        self.kf.statePost = np.array([init_x, init_y, 0, 0], dtype=np.float32)

    def update(self, x: float, y: float):
        measurement = np.array([[np.float32(x)], [np.float32(y)]])
        self.kf.correct(measurement)
        prediction = self.kf.predict()
        return (prediction[0][0], prediction[1][0]), (prediction[2][0], prediction[3][0])

    def predict_future(self, frames_ahead: int = 15):
        """Predict position N frames into the future based on current velocity."""
        state = self.kf.statePost
        px = state[0][0] + state[2][0] * frames_ahead
        py = state[1][0] + state[3][0] * frames_ahead
        return (float(px), float(py))


# ────────────────────────────────────────────────────────────
# Detection Data Class
# ────────────────────────────────────────────────────────────
class Detection:
    def __init__(self, bbox, class_name, confidence, class_id, track_id=-1):
        self.bbox = bbox  # (x1, y1, x2, y2)
        self.class_name = class_name
        self.confidence = confidence
        self.class_id = class_id
        self.hazard_type = HAZARD_CLASSES.get(class_name, "UNKNOWN")
        # Bottom-center is anchor point for ground-plane position
        self.anchor = ((bbox[0] + bbox[2]) // 2, bbox[3])
        self.center = ((bbox[0] + bbox[2]) // 2, (bbox[1] + bbox[3]) // 2)
        self.zone = "OUTSIDE"
        self.track_id = track_id
        
        # Physics & Homography attributes
        self.ground_pos_m = (0.0, 0.0)    # Ground coordinates in meters (X, Y)
        self.distance_m = 0.0              # Real-world distance in meters
        self.speed_kmh = 0.0              # Speed in km/h
        self.predicted_future_pt = self.center
        self.ttc_sec = float('inf')       # Time-to-Collision in seconds
        self.is_critical = False          # High priority danger trigger

    @property
    def distance_est(self):
        return self.distance_m

    @property
    def priority(self):
        return HAZARD_PRIORITY.get(self.hazard_type, 5)


# ────────────────────────────────────────────────────────────
# Main Detection & Analytics Engine
# ────────────────────────────────────────────────────────────
class DetectionEngine:
    def __init__(self, model_path: str = "yolov8n.pt", confidence_threshold: float = 0.35):
        self.model = YOLO(model_path)
        self.confidence_threshold = confidence_threshold
        self.class_names = self.model.names
        self.last_inference_ms = 0.0
        
        # Track filters
        self.kalman_filters: dict[int, ObjectKalmanFilter] = {}
        self.prev_positions_m: dict[int, tuple[float, float, float]] = {} # id -> (x_m, y_m, timestamp)
        
        # Homography Matrix setup
        self.H_matrix = None
        self.calibration_pts = None

    def update_homography(self, src_pts: np.ndarray, dst_size_m: tuple[float, float] = (3.0, 30.0)):
        """
        Compute 3x3 Homography matrix mapping 4 screen coordinates (trapezoid)
        to a top-down rectangular ground space in meters (width, depth).
        """
        w_m, d_m = dst_size_m
        dst_pts = np.float32([
            [0, 0],          # Top-left
            [w_m, 0],        # Top-right
            [w_m, d_m],      # Bottom-right
            [0, d_m]         # Bottom-left
        ])
        self.src_pts = np.float32(src_pts)
        self.H_matrix, _ = cv2.findHomography(self.src_pts, dst_pts)

    def screen_to_ground(self, pixel_x: float, pixel_y: float) -> tuple[float, float]:
        """Transform screen pixel (x, y) to ground space (meters)."""
        if self.H_matrix is None:
            return (0.0, 0.0)
        pt = np.array([[[pixel_x, pixel_y]]], dtype=np.float32)
        transformed = cv2.perspectiveTransform(pt, self.H_matrix)
        gx, gy = transformed[0][0]
        return float(gx), float(gy)

    def detect_and_track(self, frame: np.ndarray, track_polygon: np.ndarray = None, fps: float = 30.0) -> list[Detection]:
        t0 = time.time()
        
        # Use YOLOv8 native ByteTrack
        results = self.model.track(
            frame, 
            conf=self.confidence_threshold, 
            persist=True, 
            tracker="bytetrack.yaml", 
            verbose=False
        )
        
        self.last_inference_ms = (time.time() - t0) * 1000.0
        detections: list[Detection] = []
        now = time.time()

        if results and len(results) > 0 and results[0].boxes is not None:
            boxes = results[0].boxes
            for box in boxes:
                x1, y1, x2, y2 = box.xyxy[0].cpu().numpy().astype(int)
                conf = float(box.conf[0])
                cls_id = int(box.cls[0])
                cls_name = self.class_names.get(cls_id, "unknown")
                
                track_id = int(box.id[0]) if box.id is not None else -1

                det = Detection(
                    bbox=(int(x1), int(y1), int(x2), int(y2)),
                    class_name=cls_name,
                    confidence=conf,
                    class_id=cls_id,
                    track_id=track_id,
                )

                # 1. Zone Spatial Test (Is anchor inside track polygon?)
                if track_polygon is not None and len(track_polygon) >= 3:
                    inside = cv2.pointPolygonTest(track_polygon, (float(det.anchor[0]), float(det.anchor[1])), False) >= 0
                    det.zone = "HAZARD" if inside else "OUTSIDE"

                # 2. Homography Ground Distance & Speed Computation
                if self.H_matrix is not None:
                    gx, gy = self.screen_to_ground(det.anchor[0], det.anchor[1])
                    det.ground_pos_m = (gx, gy)
                    det.distance_m = float(np.sqrt(gx**2 + gy**2))

                    if track_id != -1 and track_id in self.prev_positions_m:
                        prev_x, prev_y, prev_t = self.prev_positions_m[track_id]
                        dt = max(now - prev_t, 1.0 / fps)
                        dist_moved_m = np.sqrt((gx - prev_x)**2 + (gy - prev_y)**2)
                        speed_ms = dist_moved_m / dt
                        det.speed_kmh = speed_ms * 3.6
                    
                    if track_id != -1:
                        self.prev_positions_m[track_id] = (gx, gy, now)

                # 3. Kalman Filtering & Future Position Prediction
                if track_id != -1:
                    if track_id not in self.kalman_filters:
                        self.kalman_filters[track_id] = ObjectKalmanFilter(det.center[0], det.center[1])
                    
                    kf = self.kalman_filters[track_id]
                    _, (vx, vy) = kf.update(det.center[0], det.center[1])
                    future_px, future_py = kf.predict_future(frames_ahead=int(fps * 1.0)) # 1 second ahead
                    det.predicted_future_pt = (int(future_px), int(future_py))

                    # 4. Time-to-Collision (TTC) Logic
                    if track_polygon is not None and det.zone == "OUTSIDE":
                        # Check if future predicted point enters hazard polygon
                        will_intrude = cv2.pointPolygonTest(track_polygon, (float(future_px), float(future_py)), False) >= 0
                        if will_intrude and det.speed_kmh > 1.0:
                            # Estimate seconds to entry
                            det.ttc_sec = max(0.5, round(1.0 / (det.speed_kmh / 10.0), 1))
                            if det.ttc_sec <= 3.0:
                                det.is_critical = True

                if det.zone == "HAZARD":
                    det.is_critical = True

                detections.append(det)

        detections.sort(key=lambda d: (d.priority, -d.confidence))
        return detections
