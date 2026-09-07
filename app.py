"""
app.py - Redesigned AI Railway Safety Surveillance System v2.0
================================================================
Interactive Streamlit Dashboard with Computer Graphics & Analytics Focus
"""

import os
import time
from datetime import datetime
from collections import deque

import cv2
import numpy as np
import streamlit as st
import plotly.graph_objects as go

from detection_engine import DetectionEngine
from graphics_engine import GraphicsEngine, render_pipeline
from multimedia_audio import MultimediaManager

# ════════════════════════════════════════════════════════════
# STREAMLIT PAGE CONFIGURATION & CUSTOM THEME
# ════════════════════════════════════════════════════════════
st.set_page_config(
    page_title="AI Railway Safety Surveillance v2.0",
    page_icon="🚂",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Custom CSS for dark modern theme & glowing alert banners
st.markdown("""
<style>
    .stApp { background-color: #0b0f19; color: #e2e8f0; }
    .stSidebar { background-color: #111827; }
    
    /* Hero Header */
    .hero-banner {
        background: linear-gradient(135deg, #1e1b4b 0%, #0f172a 100%);
        border: 1px solid #312e81;
        padding: 18px 24px;
        border-radius: 12px;
        margin-bottom: 20px;
        box-shadow: 0 4px 20px rgba(0, 0, 0, 0.4);
    }
    .hero-title { color: #38bdf8 !important; font-size: 1.8rem; font-weight: 700; margin: 0; }
    .hero-subtitle { color: #94a3b8; font-size: 0.9rem; margin-top: 4px; }
    
    /* Glowing Red Hazard Banner */
    .hazard-banner {
        background: linear-gradient(90deg, #991b1b 0%, #7f1d1d 100%);
        color: #ffffff;
        border: 2px solid #ef4444;
        padding: 12px 20px;
        border-radius: 8px;
        font-weight: bold;
        font-size: 1.2rem;
        margin-bottom: 15px;
        box-shadow: 0 0 15px rgba(239, 68, 68, 0.5);
        animation: pulse 1.5s infinite;
    }
    @keyframes pulse {
        0% { box-shadow: 0 0 10px rgba(239, 68, 68, 0.4); }
        50% { box-shadow: 0 0 25px rgba(239, 68, 68, 0.8); }
        100% { box-shadow: 0 0 10px rgba(239, 68, 68, 0.4); }
    }
    
    /* Event Log Table */
    .event-log-container {
        background-color: #0f172a;
        border: 1px solid #1e293b;
        border-radius: 8px;
        padding: 10px;
        max-height: 250px;
        overflow-y: auto;
        font-family: monospace;
        font-size: 0.85rem;
    }
    .log-critical { color: #f87171; font-weight: bold; }
    .log-warning { color: #fbbf24; }
</style>
""", unsafe_allow_html=True)


# ════════════════════════════════════════════════════════════
# SESSION STATE INITIALIZATION
# ════════════════════════════════════════════════════════════
def init_session_state():
    defaults = {
        "running": False,
        "engine": None,
        "graphics": None,
        "multimedia": None,
        "fps_history": deque(maxlen=60),
        "event_log": [],
        "confidence_values": [],
        "frame_count": 0,
        "total_hazards": 0,
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v

init_session_state()


# ════════════════════════════════════════════════════════════
# SIDEBAR CONTROLS & DYNAMIC CALIBRATION
# ════════════════════════════════════════════════════════════
with st.sidebar:
    st.markdown("## 🚂 System Configuration")
    st.markdown("---")

    # 1. Video Source
    st.markdown("### 📹 Input Source")
    source_type = st.radio("Source Type", ["Video File", "Webcam", "RTSP Stream"])
    video_source = None

    if source_type == "Video File":
        uploaded = st.file_uploader("Upload MP4 Video", type=["mp4", "avi", "mov"])
        file_path_input = st.text_input("Or Enter Local File Path", value=r"test_videos\clip1.mp4")
        if uploaded is not None:
            temp_path = os.path.join("recordings", "uploaded_input.mp4")
            os.makedirs("recordings", exist_ok=True)
            with open(temp_path, "wb") as f:
                f.write(uploaded.read())
            video_source = temp_path
        elif file_path_input:
            video_source = file_path_input
    elif source_type == "Webcam":
        cam_idx = st.number_input("Camera Index", 0, 5, 0)
        video_source = int(cam_idx)
    elif source_type == "RTSP Stream":
        video_source = st.text_input("RTSP Stream URL", placeholder="rtsp://...")

    st.markdown("---")

    # 2. Interactive Track ROI Calibration Sliders
    st.markdown("### 🎯 Track ROI Calibration")
    st.caption("Adjust the cyan safety polygon corners on screen")
    top_w_pct = st.slider("Top Width (%)", 10, 90, 30)
    bot_w_pct = st.slider("Bottom Width (%)", 20, 100, 80)
    top_y_pct = st.slider("Top Y Position (%)", 10, 80, 45)
    bot_y_pct = st.slider("Bottom Y Position (%)", 50, 100, 95)

    st.markdown("---")

    # 3. Graphics & Layer Toggles
    st.markdown("### 🎨 Graphics & Analytics Layers")
    show_heatmap = st.checkbox("Intrusion Heatmap Layer", value=False)
    show_trajectory = st.checkbox("Kalman Trajectory Prediction", value=True)
    conf_thresh = st.slider("Detection Confidence", 0.15, 0.90, 0.35, 0.05)

    st.markdown("---")

    # 4. Start / Stop Buttons
    col1, col2 = st.columns(2)
    with col1:
        start_btn = st.button("▶ START", use_container_width=True, type="primary")
    with col2:
        stop_btn = st.button("⏹ STOP", use_container_width=True)


# ════════════════════════════════════════════════════════════
# HEADER & HERO BANNER
# ════════════════════════════════════════════════════════════
st.markdown("""
<div class="hero-banner">
    <div class="hero-title">AI-Powered Railway Safety System</div>
    <div class="hero-subtitle">Real-Time Computer Vision & Homography Analytics Platform</div>
</div>
""", unsafe_allow_html=True)

# Dynamic Alert Banner Container
alert_container = st.empty()


# ════════════════════════════════════════════════════════════
# MAIN DASHBOARD LAYOUT
# ════════════════════════════════════════════════════════════
video_col, metrics_col = st.columns([3, 1])

with video_col:
    st.markdown("#### 📺 Live Surveillance Feed")
    video_placeholder = st.empty()

with metrics_col:
    st.markdown("#### 📊 Real-Time Metrics")
    fps_m = st.empty()
    inf_m = st.empty()
    det_m = st.empty()
    haz_m = st.empty()

chart_col, log_col = st.columns([1, 1])

with chart_col:
    st.markdown("#### 📈 Confidence Distribution")
    chart_placeholder = st.empty()

with log_col:
    st.markdown("#### 📋 Hazard Incident Log")
    log_placeholder = st.empty()


# ════════════════════════════════════════════════════════════
# START / STOP HANDLERS
# ════════════════════════════════════════════════════════════
if stop_btn:
    st.session_state.running = False
    if st.session_state.multimedia:
        st.session_state.multimedia.shutdown()
    st.info("⏹ Surveillance system stopped.")

if start_btn:
    if not video_source:
        st.error("⚠ Please select a valid video source.")
    else:
        if source_type == "Video File" and isinstance(video_source, str) and not video_source.startswith(("http", "rtsp")):
            if not os.path.exists(video_source):
                st.error(f"❌ Video file not found: {video_source}")
                st.session_state.running = False
            else:
                st.session_state.running = True
        else:
            st.session_state.running = True

        if st.session_state.running:
            st.session_state.engine = DetectionEngine(confidence_threshold=conf_thresh)
            st.session_state.graphics = GraphicsEngine()
            st.session_state.multimedia = MultimediaManager(output_dir="recordings")
            st.session_state.event_log = []
            st.session_state.frame_count = 0
            st.session_state.total_hazards = 0
            st.toast("🚀 Surveillance system initialized!", icon="✅")


# ════════════════════════════════════════════════════════════
# MAIN VIDEO PROCESSING LOOP
# ════════════════════════════════════════════════════════════
if st.session_state.running and st.session_state.engine is not None:
    engine: DetectionEngine = st.session_state.engine
    graphics: GraphicsEngine = st.session_state.graphics
    multimedia: MultimediaManager = st.session_state.multimedia

    cap = cv2.VideoCapture(video_source)

    if not cap.isOpened():
        st.error("❌ Failed to open video stream.")
        st.session_state.running = False
    else:
        prev_time = time.time()

        while st.session_state.running:
            ret, frame = cap.read()
            if not ret:
                if source_type == "Video File":
                    cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
                    continue
                else:
                    break

            st.session_state.frame_count += 1
            h, w = frame.shape[:2]

            # ── 1. Construct Dynamic Track Polygon from UI Sliders ──
            top_w = int(w * (top_w_pct / 100.0))
            bot_w = int(w * (bot_w_pct / 100.0))
            top_y = int(h * (top_y_pct / 100.0))
            bot_y = int(h * (bot_y_pct / 100.0))
            cx = w // 2

            track_polygon = np.array([
                [cx - top_w // 2, top_y],  # Top-left
                [cx + top_w // 2, top_y],  # Top-right
                [cx + bot_w // 2, bot_y],  # Bottom-right
                [cx - bot_w // 2, bot_y]   # Bottom-left
            ], dtype=np.int32)

            # Update Homography Ground Mapping
            engine.update_homography(track_polygon, dst_size_m=(3.0, 30.0))

            # ── 2. Run Inference & Analytics ─────────────────────────
            current_time = time.time()
            dt = current_time - prev_time
            fps = 1.0 / dt if dt > 0 else 30.0
            prev_time = current_time
            st.session_state.fps_history.append(fps)

            detections = engine.detect_and_track(frame, track_polygon, fps)
            hazards = [d for d in detections if d.is_critical or d.zone == "HAZARD"]

            # ── 3. Render Graphics Overlays ──────────────────────────
            rendered_frame = render_pipeline(
                frame.copy(),
                detections,
                track_polygon,
                graphics,
                show_heatmap=show_heatmap,
                show_trajectory=show_trajectory
            )

            # ── 4. Trigger Multimedia Alerts & Snapshots ─────────────
            multimedia.process_hazards(detections, rendered_frame, fps)

            # ── 5. Streamlit UI Updates ──────────────────────────────
            display_rgb = cv2.cvtColor(rendered_frame, cv2.COLOR_BGR2RGB)
            video_placeholder.image(display_rgb, channels="RGB", use_container_width=True)

            # Render UI Glowing Alert Banner
            if hazards:
                crit_h = hazards[0]
                alert_container.markdown(
                    f'<div class="hazard-banner">🚨 ALERT: {crit_h.class_name.upper()} DETECTED ON TRACK!</div>',
                    unsafe_allow_html=True
                )
            else:
                alert_container.empty()

            # Update Metrics & Charts
            if st.session_state.frame_count % 5 == 0:
                avg_fps = np.mean(list(st.session_state.fps_history)) if st.session_state.fps_history else 0
                fps_m.metric("FPS", f"{avg_fps:.1f}")
                inf_m.metric("Inference", f"{engine.last_inference_ms:.1f} ms")
                det_m.metric("Active Objects", len(detections))
                haz_m.metric("Hazards Detected", len(hazards))

                # Log hazards
                for h_item in hazards:
                    st.session_state.event_log.append({
                        "time": datetime.now().strftime("%H:%M:%S"),
                        "class": h_item.class_name,
                        "zone": h_item.zone,
                        "dist": f"{h_item.distance_m:.1f}m"
                    })

                if st.session_state.event_log:
                    log_lines = []
                    for evt in reversed(st.session_state.event_log[-15:]):
                        log_lines.append(f'<div class="log-critical">[{evt["time"]}] HAZARD: {evt["class"].upper()} inside track zone ({evt["dist"]})</div>')
                    log_placeholder.markdown(f'<div class="event-log-container">{"".join(log_lines)}</div>', unsafe_allow_html=True)

        cap.release()

else:
    video_placeholder.info("Click ▶ **START** in the sidebar to launch the surveillance engine.")
