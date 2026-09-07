"""
server.py - FastAPI REST Server for RailAI Safety Surveillance System
======================================================================
Provides asynchronous REST endpoints for video upload, AI analysis job queue,
progress tracking, media streaming, and analytics.

Integrates directly with:
  - detection_engine.py (YOLOv8 ByteTrack + Homography + Kalman Filter TTC)
  - graphics_engine.py (Cyan Track ROI + Red Box + Alert Banner + Heatmap)
  - multimedia_audio.py (Snapshots & Clips)
"""

import os
import uuid
import time
import threading
from typing import Dict, Any, List, Optional
from datetime import datetime

import cv2
import numpy as np
from fastapi import FastAPI, UploadFile, File, Form, BackgroundTasks, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel

from detection_engine import DetectionEngine
from graphics_engine import GraphicsEngine, render_pipeline
from multimedia_audio import MultimediaManager

# ════════════════════════════════════════════════════════════
# DIRECTORY STRUCTURE & APP CONFIGURATION
# ════════════════════════════════════════════════════════════
UPLOAD_DIR = os.path.join("recordings", "uploads")
PROCESSED_DIR = os.path.join("recordings", "processed")
SNAPSHOT_DIR = os.path.join("recordings", "snapshots")

os.makedirs(UPLOAD_DIR, exist_ok=True)
os.makedirs(PROCESSED_DIR, exist_ok=True)
os.makedirs(SNAPSHOT_DIR, exist_ok=True)

app = FastAPI(
    title="RailAI Safety Intelligence API",
    description="REST API server for Railway Video AI Surveillance & Hazard Analytics",
    version="2.0.0"
)

# CORS Configuration for Next.js frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allows Next.js dev server on port 3000
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# In-memory Job & Incident Store
JOBS: Dict[str, Dict[str, Any]] = {}


# ════════════════════════════════════════════════════════════
# BACKGROUND VIDEO AI PROCESSING WORKER
# ════════════════════════════════════════════════════════════
def process_video_worker(
    job_id: str,
    input_path: str,
    output_path: str,
    top_w_pct: float,
    bot_w_pct: float,
    top_y_pct: float,
    bot_y_pct: float,
    conf_thresh: float,
    show_heatmap: bool,
    show_trajectory: bool,
):
    try:
        JOBS[job_id]["status"] = "processing"
        JOBS[job_id]["progress"] = 0.0

        cap = cv2.VideoCapture(input_path)
        if not cap.isOpened():
            JOBS[job_id]["status"] = "failed"
            JOBS[job_id]["error"] = "Failed to open video file"
            return

        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        src_fps = cap.get(cv2.CAP_PROP_FPS)
        if src_fps <= 0 or np.isnan(src_fps):
            src_fps = 25.0

        w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

        raw_temp_output = output_path.replace(".mp4", "_temp.mp4")

        # Use mp4v codec for fast raw frame rendering
        fourcc = cv2.VideoWriter_fourcc(*"mp4v")
        writer = cv2.VideoWriter(raw_temp_output, fourcc, src_fps, (w, h))

        engine = DetectionEngine(confidence_threshold=conf_thresh)
        graphics = GraphicsEngine(width=w, height=h)
        multimedia = MultimediaManager(output_dir="recordings")

        frame_idx = 0
        detections_timeline: List[Dict[str, Any]] = []
        people_count = 0
        obstacle_count = 0
        intrusion_count = 0
        max_hazard_severity = 0  # 0: None, 1: Medium, 2: High, 3: Critical

        last_logged_time = -1.0

        while cap.isOpened():
            ret, frame = cap.read()
            if not ret:
                break

            frame_idx += 1
            timestamp_sec = round(frame_idx / src_fps, 2)

            # Construct Track ROI Polygon
            top_w = int(w * (top_w_pct / 100.0))
            bot_w = int(w * (bot_w_pct / 100.0))
            top_y = int(h * (top_y_pct / 100.0))
            bot_y = int(h * (bot_y_pct / 100.0))
            cx = w // 2

            track_polygon = np.array([
                [cx - top_w // 2, top_y],
                [cx + top_w // 2, top_y],
                [cx + bot_w // 2, bot_y],
                [cx - bot_w // 2, bot_y]
            ], dtype=np.int32)

            engine.update_homography(track_polygon, dst_size_m=(3.0, 30.0))

            # Run AI Inference & ByteTrack Tracking
            detections = engine.detect_and_track(frame, track_polygon, src_fps)
            hazards = [d for d in detections if d.is_critical or d.zone == "HAZARD"]

            # Render Computer Graphics Pipeline
            rendered = render_pipeline(
                frame.copy(),
                detections,
                track_polygon,
                graphics,
                show_heatmap=show_heatmap,
                show_trajectory=show_trajectory
            )

            writer.write(rendered)
            multimedia.process_hazards(detections, rendered, src_fps)

            # Record timeline events (deduplicated by timestamp window)
            if hazards and (timestamp_sec - last_logged_time >= 1.0):
                last_logged_time = timestamp_sec
                for det in hazards:
                    if det.hazard_type == "HUMAN":
                        people_count += 1
                    elif det.hazard_type in ("OBSTACLE", "DEBRIS", "ANIMAL"):
                        obstacle_count += 1
                    
                    if det.zone == "HAZARD":
                        intrusion_count += 1
                        max_hazard_severity = max(max_hazard_severity, 3)
                    elif det.is_critical:
                        max_hazard_severity = max(max_hazard_severity, 2)
                    else:
                        max_hazard_severity = max(max_hazard_severity, 1)

                    # Format MM:SS timestamp string
                    mins = int(timestamp_sec // 60)
                    secs = int(timestamp_sec % 60)
                    time_str = f"{mins:02d}:{secs:02d}"

                    detections_timeline.append({
                        "timestamp": timestamp_sec,
                        "time_formatted": time_str,
                        "type": det.hazard_type,
                        "class_name": det.class_name.title(),
                        "zone": det.zone,
                        "confidence": round(det.confidence, 2),
                        "distance_m": round(det.distance_m, 1),
                        "is_critical": det.is_critical
                    })

            # Update Job Progress
            if total_frames > 0:
                JOBS[job_id]["progress"] = round((frame_idx / total_frames) * 100.0, 1)

        cap.release()
        writer.release()
        multimedia.shutdown()

        # Re-encode to HTML5 web-compatible H.264 (yuv420p)
        try:
            import subprocess
            import imageio_ffmpeg
            ffmpeg_exe = imageio_ffmpeg.get_ffmpeg_exe()
            cmd = [
                ffmpeg_exe, "-y",
                "-i", raw_temp_output,
                "-c:v", "libx264",
                "-pix_fmt", "yuv420p",
                "-preset", "ultrafast",
                output_path
            ]
            subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
            if os.path.exists(raw_temp_output):
                os.remove(raw_temp_output)
        except Exception as ffmpeg_err:
            print("FFmpeg re-encode fallback:", ffmpeg_err)
            if os.path.exists(raw_temp_output):
                if os.path.exists(output_path):
                    os.remove(output_path)
                os.rename(raw_temp_output, output_path)

        # Determine Risk Level
        risk_level = "LOW"
        if max_hazard_severity == 3:
            risk_level = "CRITICAL"
        elif max_hazard_severity == 2:
            risk_level = "HIGH"
        elif max_hazard_severity == 1 or len(detections_timeline) > 0:
            risk_level = "MEDIUM"

        processed_filename = os.path.basename(output_path)
        
        JOBS[job_id]["status"] = "completed"
        JOBS[job_id]["progress"] = 100.0
        JOBS[job_id]["completed_at"] = datetime.now().isoformat()
        JOBS[job_id]["result"] = {
            "job_id": job_id,
            "filename": JOBS[job_id]["original_filename"],
            "processed_video_url": f"/api/media/{processed_filename}",
            "risk_level": risk_level,
            "duration_sec": round(total_frames / src_fps, 1),
            "summary": {
                "people_detected": people_count,
                "obstacles_detected": obstacle_count,
                "track_intrusions": intrusion_count,
                "total_incidents": len(detections_timeline)
            },
            "timeline": detections_timeline
        }

    except Exception as e:
        JOBS[job_id]["status"] = "failed"
        JOBS[job_id]["error"] = str(e)


# ════════════════════════════════════════════════════════════
# REST ENDPOINTS
# ════════════════════════════════════════════════════════════

@app.get("/")
def root():
    return {"system": "RailAI Safety Intelligence API", "status": "online", "version": "2.0.0"}


@app.post("/api/analyze")
async def analyze_video(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    top_w_pct: float = Form(30.0),
    bot_w_pct: float = Form(80.0),
    top_y_pct: float = Form(45.0),
    bot_y_pct: float = Form(95.0),
    conf_thresh: float = Form(0.35),
    show_heatmap: bool = Form(False),
    show_trajectory: bool = Form(True),
):
    """Upload pre-recorded railway video and queue AI analysis job."""
    if not file.filename.lower().endswith((".mp4", ".avi", ".mov", ".mkv")):
        raise HTTPException(status_code=400, detail="Unsupported video format. Please upload MP4, AVI, or MOV.")

    job_id = str(uuid.uuid4())[:8]
    raw_filename = f"{job_id}_raw_{file.filename}"
    processed_filename = f"{job_id}_processed.mp4"

    raw_path = os.path.join(UPLOAD_DIR, raw_filename)
    processed_path = os.path.join(PROCESSED_DIR, processed_filename)

    # Save uploaded file asynchronously
    contents = await file.read()
    with open(raw_path, "wb") as f:
        f.write(contents)

    file_size_mb = round(len(contents) / (1024 * 1024), 2)

    JOBS[job_id] = {
        "job_id": job_id,
        "status": "queued",
        "progress": 0.0,
        "original_filename": file.filename,
        "file_size_mb": file_size_mb,
        "created_at": datetime.now().isoformat(),
        "result": None,
        "error": None
    }

    # Dispatch to background thread
    background_tasks.add_task(
        process_video_worker,
        job_id,
        raw_path,
        processed_path,
        top_w_pct,
        bot_w_pct,
        top_y_pct,
        bot_y_pct,
        conf_thresh,
        show_heatmap,
        show_trajectory
    )

    return {
        "status": "queued",
        "job_id": job_id,
        "filename": file.filename,
        "file_size_mb": file_size_mb,
        "message": "Video uploaded successfully. AI processing started."
    }


@app.get("/api/job/{job_id}")
def get_job_status(job_id: str):
    """Poll progress status of an active analysis job."""
    if job_id not in JOBS:
        raise HTTPException(status_code=404, detail="Job ID not found")
    
    job = JOBS[job_id]
    return {
        "job_id": job_id,
        "status": job["status"],
        "progress": job["progress"],
        "error": job["error"],
        "result": job["result"] if job["status"] == "completed" else None
    }


@app.get("/api/incidents")
def list_incidents():
    """Retrieve history of all analyzed video incidents."""
    incidents = []
    for jid, job in JOBS.items():
        if job["status"] == "completed" and job["result"] is not None:
            res = job["result"]
            incidents.append({
                "job_id": jid,
                "filename": job["original_filename"],
                "created_at": job["created_at"],
                "risk_level": res["risk_level"],
                "duration_sec": res["duration_sec"],
                "total_incidents": res["summary"]["total_incidents"],
                "people_detected": res["summary"]["people_detected"],
                "track_intrusions": res["summary"]["track_intrusions"],
            })
    return {"incidents": sorted(incidents, key=lambda x: x["created_at"], reverse=True)}


@app.get("/api/analytics")
def get_analytics():
    """Retrieve aggregate safety metrics across all analyzed videos."""
    completed_jobs = [j["result"] for j in JOBS.values() if j["status"] == "completed" and j["result"] is not None]
    
    total_videos = len(completed_jobs)
    total_incidents = sum(j["summary"]["total_incidents"] for j in completed_jobs)
    total_intrusions = sum(j["summary"]["track_intrusions"] for j in completed_jobs)
    
    risk_dist = {"CRITICAL": 0, "HIGH": 0, "MEDIUM": 0, "LOW": 0}
    for j in completed_jobs:
        risk = j["risk_level"]
        risk_dist[risk] = risk_dist.get(risk, 0) + 1

    return {
        "total_videos_analyzed": total_videos,
        "total_incidents_detected": total_incidents,
        "total_track_intrusions": total_intrusions,
        "risk_distribution": risk_dist
    }


@app.get("/api/media/{filename}")
def stream_media(filename: str):
    """Serve processed videos or snapshots."""
    # Check processed dir
    p_path = os.path.join(PROCESSED_DIR, filename)
    if os.path.exists(p_path):
        return FileResponse(p_path, media_type="video/mp4")
    
    # Check snapshot dir
    s_path = os.path.join(SNAPSHOT_DIR, filename)
    if os.path.exists(s_path):
        return FileResponse(s_path, media_type="image/png")
        
    raise HTTPException(status_code=404, detail="Media file not found")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
