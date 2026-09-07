"""
multimedia_audio.py - Audio Alert Manager & Multimedia Snapshot Recorder
=========================================================================
Handles two multimedia subsystems:

  1. Audio Alerts
     - pyttsx3 text-to-speech for spoken hazard announcements
     - pygame mixer for synthesized warning tones (sine-wave beeps)
     - Cooldown timers to prevent alert spam

  2. Snapshot & Clip Recorder
     - Automatic annotated frame capture on hazard detection
     - Timestamped watermarked PNG snapshots
     - Video clip recording of hazard events

Computer Graphics / Multimedia Concepts:
  - Audio frequency synthesis via numpy sine-wave generation
  - PIL-based text watermarking on snapshot images
  - Thread-safe audio engine to avoid blocking the render loop
=========================================================================
"""

import os
import time
import threading
import numpy as np
import cv2

# ── Optional imports with graceful fallbacks ─────────────────
try:
    import pyttsx3
    _HAS_TTS = True
except ImportError:
    _HAS_TTS = False

try:
    import pygame
    import pygame.mixer
    _HAS_PYGAME = True
except ImportError:
    _HAS_PYGAME = False

try:
    from PIL import Image, ImageDraw, ImageFont
    _HAS_PIL = True
except ImportError:
    _HAS_PIL = False


# ════════════════════════════════════════════════════════════
# AUDIO ALERT MANAGER
# ════════════════════════════════════════════════════════════
class AudioAlertManager:
    """
    Thread-safe audio alert system combining:
      - TTS voice announcements (pyttsx3)
      - Synthesized warning tones (pygame.mixer)

    All audio runs on background threads to keep the rendering loop
    non-blocking.  A per-category cooldown prevents overlapping alerts.
    """

    def __init__(self, cooldown_sec: float = 5.0, tts_enabled: bool = True,
                 tone_enabled: bool = True):
        self.cooldown_sec = cooldown_sec
        self.tts_enabled = tts_enabled and _HAS_TTS
        self.tone_enabled = tone_enabled and _HAS_PYGAME
        self._last_alert_time: dict[str, float] = {}
        self._tts_lock = threading.Lock()
        self._tts_engine = None

        # ── Initialise TTS engine (single instance) ──────────
        if self.tts_enabled:
            try:
                self._tts_engine = pyttsx3.init()
                self._tts_engine.setProperty("rate", 170)
                self._tts_engine.setProperty("volume", 0.9)
            except Exception:
                self.tts_enabled = False

        # ── Initialise pygame mixer for tone generation ──────
        if self.tone_enabled:
            try:
                pygame.mixer.init(frequency=44100, size=-16, channels=1, buffer=512)
            except Exception:
                self.tone_enabled = False

    # ── Cooldown gate ────────────────────────────────────────
    def _can_alert(self, category: str) -> bool:
        now = time.time()
        last = self._last_alert_time.get(category, 0)
        if now - last >= self.cooldown_sec:
            self._last_alert_time[category] = now
            return True
        return False

    # ── Synthesised warning tone ─────────────────────────────
    def _generate_tone(self, frequency: float = 880.0,
                       duration_ms: int = 400, volume: float = 0.6):
        """
        Generate a sine-wave warning beep at the specified frequency.

        Audio Synthesis Technique:
          samples[i] = volume * sin(2π * frequency * i / sample_rate)

        The raw PCM buffer is loaded into a pygame Sound object for playback.
        """
        if not self.tone_enabled:
            return
        try:
            sample_rate = 44100
            n_samples = int(sample_rate * duration_ms / 1000)
            t = np.linspace(0, duration_ms / 1000, n_samples, endpoint=False)

            # Generate sine wave
            wave = volume * np.sin(2 * np.pi * frequency * t)

            # Apply fade-in / fade-out envelope to avoid clicks
            fade_len = min(n_samples // 10, 500)
            wave[:fade_len] *= np.linspace(0, 1, fade_len)
            wave[-fade_len:] *= np.linspace(1, 0, fade_len)

            # Convert to 16-bit signed PCM
            pcm = (wave * 32767).astype(np.int16)

            sound = pygame.mixer.Sound(buffer=pcm.tobytes())
            sound.play()
        except Exception:
            pass

    # ── TTS speech ───────────────────────────────────────────
    def _speak(self, text: str):
        """Run TTS on a background thread to avoid blocking."""
        if not self.tts_enabled or self._tts_engine is None:
            return

        def _run():
            with self._tts_lock:
                try:
                    self._tts_engine.say(text)
                    self._tts_engine.runAndWait()
                except Exception:
                    pass

        thread = threading.Thread(target=_run, daemon=True)
        thread.start()

    # ── Public API ───────────────────────────────────────────
    def trigger_alert(self, hazard_type: str, zone: str,
                      class_name: str, distance: float = 0.0):
        """
        Fire an audio alert for a detected hazard.

        Parameters:
            hazard_type – HUMAN, ANIMAL, OBSTACLE, DEBRIS
            zone        – HAZARD, CAUTION, SAFE
            class_name  – Detected COCO class label
            distance    – Estimated distance in metres
        """
        category_key = f"{hazard_type}_{zone}"
        if not self._can_alert(category_key):
            return

        # ── Tone frequency mapped to urgency ─────────────────
        tone_freq = {"HAZARD": 1200, "CAUTION": 800, "SAFE": 500}.get(zone, 600)
        tone_dur = {"HAZARD": 500, "CAUTION": 350, "SAFE": 200}.get(zone, 300)

        if self.tone_enabled:
            threading.Thread(
                target=self._generate_tone,
                args=(tone_freq, tone_dur, 0.5),
                daemon=True,
            ).start()

        # ── TTS announcement ─────────────────────────────────
        zone_label = {"HAZARD": "Hazard Zone", "CAUTION": "Caution Zone",
                      "SAFE": "Safe Zone"}.get(zone, zone)
        dist_str = f" at approximately {int(distance)} metres" if distance > 0 else ""
        speech = f"WARNING: {hazard_type.title()} detected. {class_name.title()} in {zone_label}{dist_str}."
        self._speak(speech)

    def shutdown(self):
        """Clean up audio resources."""
        if self.tone_enabled:
            try:
                pygame.mixer.quit()
            except Exception:
                pass


# ════════════════════════════════════════════════════════════
# SNAPSHOT & CLIP RECORDER
# ════════════════════════════════════════════════════════════
class SnapshotRecorder:
    """
    Automatically captures annotated frame snapshots and short video clips
    when a hazard threshold is breached.

    Snapshots:
      - Saved as timestamped PNGs with a text watermark overlay.
      - Watermark uses PIL for high-quality text rendering.

    Video Clips:
      - Records a configurable-length clip around the hazard event.
      - Uses OpenCV VideoWriter with MJPG codec for broad compatibility.
    """

    def __init__(self, output_dir: str = "recordings",
                 cooldown_sec: float = 10.0,
                 clip_duration_sec: float = 5.0):
        self.output_dir = output_dir
        self.snapshot_dir = os.path.join(output_dir, "snapshots")
        self.clip_dir = os.path.join(output_dir, "clips")
        self.cooldown_sec = cooldown_sec
        self.clip_duration = clip_duration_sec
        self._last_capture_time: float = 0.0
        self._clip_writer = None
        self._clip_end_time: float = 0.0
        self._event_log: list[dict] = []

        os.makedirs(self.snapshot_dir, exist_ok=True)
        os.makedirs(self.clip_dir, exist_ok=True)

    # ── Watermark helpers ────────────────────────────────────
    def _add_watermark(self, frame: np.ndarray, text: str) -> np.ndarray:
        """
        Overlay a semi-transparent watermark banner on the frame.

        Uses PIL for high-quality anti-aliased text rendering,
        then composites back onto the OpenCV BGR frame.
        """
        annotated = frame.copy()
        h, w = annotated.shape[:2]

        # Draw dark banner at top
        overlay = annotated.copy()
        cv2.rectangle(overlay, (0, 0), (w, 36), (20, 20, 20), -1)
        cv2.addWeighted(overlay, 0.7, annotated, 0.3, 0, dst=annotated)

        cv2.putText(annotated, text, (10, 25),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.55, (0, 255, 200), 1, cv2.LINE_AA)

        return annotated

    # ── Snapshot ─────────────────────────────────────────────
    def capture_snapshot(self, frame: np.ndarray,
                         hazard_summary: str = "") -> str | None:
        """
        Save a watermarked PNG snapshot of the current frame.

        Returns the file path if saved, or None if on cooldown.
        """
        now = time.time()
        if now - self._last_capture_time < self.cooldown_sec:
            return None

        self._last_capture_time = now
        timestamp = time.strftime("%Y%m%d_%H%M%S")
        watermark_text = f"RAILWAY AI | {timestamp} | {hazard_summary}"
        annotated = self._add_watermark(frame, watermark_text)

        filename = f"hazard_{timestamp}.png"
        filepath = os.path.join(self.snapshot_dir, filename)
        cv2.imwrite(filepath, annotated)

        # Log the event
        self._event_log.append({
            "time": timestamp,
            "type": "snapshot",
            "file": filepath,
            "summary": hazard_summary,
        })

        return filepath

    # ── Video clip recording ─────────────────────────────────
    def start_clip(self, frame: np.ndarray, fps: float = 25.0):
        """Begin recording a video clip around the hazard event."""
        if self._clip_writer is not None:
            return  # Already recording

        timestamp = time.strftime("%Y%m%d_%H%M%S")
        filename = f"clip_{timestamp}.avi"
        filepath = os.path.join(self.clip_dir, filename)

        h, w = frame.shape[:2]
        fourcc = cv2.VideoWriter_fourcc(*"MJPG")
        self._clip_writer = cv2.VideoWriter(filepath, fourcc, fps, (w, h))
        self._clip_end_time = time.time() + self.clip_duration
        self._clip_filepath = filepath

        self._event_log.append({
            "time": timestamp,
            "type": "clip_start",
            "file": filepath,
        })

    def write_clip_frame(self, frame: np.ndarray):
        """Write a frame to the active clip. Auto-stops after duration expires."""
        if self._clip_writer is None:
            return

        if time.time() > self._clip_end_time:
            self.stop_clip()
            return

        self._clip_writer.write(frame)

    def stop_clip(self):
        """Finalize and close the clip writer."""
        if self._clip_writer is not None:
            self._clip_writer.release()
            self._clip_writer = None

    @property
    def is_recording(self) -> bool:
        return self._clip_writer is not None

    @property
    def event_log(self) -> list[dict]:
        return list(self._event_log)

    def shutdown(self):
        self.stop_clip()


# ════════════════════════════════════════════════════════════
# CONVENIENCE: Combined Multimedia Manager
# ════════════════════════════════════════════════════════════
class MultimediaManager:
    """
    Facade that combines AudioAlertManager and SnapshotRecorder
    into a single interface for the main application loop.
    """

    def __init__(self, output_dir: str = "recordings",
                 tts_enabled: bool = True,
                 tone_enabled: bool = True,
                 audio_cooldown: float = 5.0,
                 snapshot_cooldown: float = 10.0,
                 clip_duration: float = 5.0):
        self.audio = AudioAlertManager(
            cooldown_sec=audio_cooldown,
            tts_enabled=tts_enabled,
            tone_enabled=tone_enabled,
        )
        self.recorder = SnapshotRecorder(
            output_dir=output_dir,
            cooldown_sec=snapshot_cooldown,
            clip_duration_sec=clip_duration,
        )

    def process_hazards(self, detections, frame: np.ndarray, fps: float = 25.0):
        """
        Process a list of hazard detections:
          - Trigger audio alerts for each unique hazard
          - Capture snapshot on first hazard
          - Start clip recording if not already active
        """
        from detection_engine import Detection  # avoid circular import at top level

        hazards = [d for d in detections
                   if d.hazard_type in ("HUMAN", "ANIMAL", "OBSTACLE", "DEBRIS")
                   and d.zone in ("HAZARD", "CAUTION", "SAFE")]

        if not hazards:
            # Write clip frame if still recording from a prior event
            self.recorder.write_clip_frame(frame)
            return

        # Audio alerts for each hazard category
        alerted_categories = set()
        for det in hazards:
            cat_key = f"{det.hazard_type}_{det.zone}"
            if cat_key not in alerted_categories:
                self.audio.trigger_alert(
                    det.hazard_type, det.zone,
                    det.class_name, det.distance_est,
                )
                alerted_categories.add(cat_key)

        # Snapshot (one per cooldown window)
        summary = ", ".join(
            f"{d.class_name}@{d.zone}" for d in hazards[:3]
        )
        self.recorder.capture_snapshot(frame, summary)

        # Clip recording
        if not self.recorder.is_recording:
            self.recorder.start_clip(frame, fps)
        self.recorder.write_clip_frame(frame)

    def shutdown(self):
        self.audio.shutdown()
        self.recorder.shutdown()
