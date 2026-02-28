"""
AgriSense Robotics Scanner - Auto-Scan Orchestration

State machine that orchestrates the full ESP32-CAM scanning pipeline:
  Motor moves -> YOLO detects leaf -> Motor stops -> High-res capture ->
  Disease classification -> RAG advice -> Result broadcast -> Resume

Uses an event pub/sub system to push real-time updates to WebSocket consumers.
"""

import asyncio
import logging
import time
import base64
from datetime import datetime
from dataclasses import dataclass, field, asdict
from enum import Enum
from typing import List, Optional, Callable, Any, Dict, Tuple

logger = logging.getLogger("AgriSense.Scanner")


class ScanState(str, Enum):
    IDLE = "idle"
    CONNECTING = "connecting"
    SCANNING = "scanning"
    LEAF_DETECTED = "leaf_detected"
    CAPTURING = "capturing"
    CLASSIFYING = "classifying"
    ADVISING = "advising"
    RESULT_READY = "result_ready"
    ERROR = "error"


@dataclass
class ScanEvent:
    """Event pushed to frontends via WebSocket."""
    event_type: str  # state_change, detection, classification, advice, error
    state: str
    data: dict = field(default_factory=dict)
    timestamp: str = field(default_factory=lambda: datetime.utcnow().isoformat())

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class ScanResult:
    """Result of a single leaf detection + classification cycle."""
    scan_index: int
    detections: list  # List of Detection dicts from YOLO
    disease: Optional[str] = None
    disease_confidence: Optional[float] = None
    classification_model: Optional[str] = None
    all_predictions: Optional[dict] = None
    advice: Optional[dict] = None
    image_base64: Optional[str] = None
    timestamp: str = field(default_factory=lambda: datetime.utcnow().isoformat())

    def to_dict(self) -> dict:
        return asdict(self)


class RoboticsScanner:
    """
    Orchestrates the ESP32-CAM auto-scan pipeline.

    Dependencies are injected for testability:
    - esp32_client: ESP32Client for hardware communication
    - yolo_detector: YOLODetector for leaf detection
    - classify_fn: Callable for disease classification (vision_engine.predict_disease)
    - advice_fn: Callable for RAG advice (get_agri_advice)
    - weather_fn: Callable for weather data (get_weather_forecast)
    """

    def __init__(
        self,
        esp32_client,
        yolo_detector,
        classify_fn: Callable,
        advice_fn: Callable,
        weather_fn: Callable = None,
    ):
        self.esp32 = esp32_client
        self.yolo = yolo_detector
        self.classify = classify_fn
        self.get_advice = advice_fn
        self.get_weather = weather_fn

        self.state = ScanState.IDLE
        self._scan_task: Optional[asyncio.Task] = None
        self._subscribers: List[asyncio.Queue] = []
        self._results: List[ScanResult] = []
        self._model_type: str = "mobilenet"
        self._detection_confidence: float = 0.25
        self._scan_index: int = 0

        # Raster scan configuration
        self._pan_min: int = 0
        self._pan_max: int = 180
        self._tilt_min: int = 30
        self._tilt_max: int = 120
        self._scan_step: int = 15
        self._settle_delay: float = 0.3

        # Scan state tracking
        self._scan_positions: List[Tuple[int, int]] = []
        self._current_position_index: int = 0

    @property
    def scan_results(self) -> List[dict]:
        return [r.to_dict() for r in self._results]

    def subscribe(self) -> asyncio.Queue:
        """Subscribe to scan events. Returns a queue that receives ScanEvent dicts."""
        q: asyncio.Queue = asyncio.Queue(maxsize=100)
        self._subscribers.append(q)
        logger.info(f"WebSocket subscriber added. Total: {len(self._subscribers)}")
        return q

    def unsubscribe(self, q: asyncio.Queue):
        """Remove a subscriber queue."""
        if q in self._subscribers:
            self._subscribers.remove(q)
            logger.info(f"WebSocket subscriber removed. Total: {len(self._subscribers)}")

    async def _broadcast(self, event: ScanEvent):
        """Push event to all subscriber queues."""
        dead_queues = []
        for q in self._subscribers:
            try:
                q.put_nowait(event)
            except asyncio.QueueFull:
                dead_queues.append(q)
                logger.warning("Subscriber queue full, dropping subscriber")
        for q in dead_queues:
            self._subscribers.remove(q)

    async def _set_state(self, new_state: ScanState, data: dict = None):
        """Transition to a new state and broadcast the change."""
        self.state = new_state
        await self._broadcast(ScanEvent(
            event_type="state_change",
            state=new_state.value,
            data=data or {},
        ))

    # =========================================================================
    # Raster Pattern
    # =========================================================================

    def _generate_raster_pattern(self) -> List[Tuple[int, int]]:
        """
        Generate raster scan positions: sweep pan left-to-right, step tilt down,
        sweep right-to-left, step tilt down, repeat.

        Returns list of (pan, tilt) tuples.
        """
        positions = []
        tilt = self._tilt_min
        left_to_right = True

        while tilt <= self._tilt_max:
            if left_to_right:
                pan = self._pan_min
                while pan <= self._pan_max:
                    positions.append((pan, tilt))
                    pan += self._scan_step
            else:
                pan = self._pan_max
                while pan >= self._pan_min:
                    positions.append((pan, tilt))
                    pan -= self._scan_step

            tilt += self._scan_step
            left_to_right = not left_to_right

        logger.info(f"Generated raster pattern with {len(positions)} positions")
        return positions

    # =========================================================================
    # Public API
    # =========================================================================

    async def start_auto_scan(
        self,
        model_type: str = "mobilenet",
        detection_confidence: float = 0.25,
        pan_min: int = 0,
        pan_max: int = 180,
        tilt_min: int = 30,
        tilt_max: int = 120,
        step_size: int = 15,
    ):
        """Start the automated raster scanning loop."""
        if self.state == ScanState.SCANNING:
            logger.warning("Auto-scan already running")
            return

        if not self.esp32.is_connected:
            raise ConnectionError("ESP32-CAM not connected")
        if not self.yolo.is_loaded:
            raise RuntimeError("YOLO detector not loaded")

        self._model_type = model_type
        self._detection_confidence = detection_confidence
        self._pan_min = pan_min
        self._pan_max = pan_max
        self._tilt_min = tilt_min
        self._tilt_max = tilt_max
        self._scan_step = step_size
        self._results = []
        self._scan_index = 0

        # Generate raster scan positions
        self._scan_positions = self._generate_raster_pattern()
        self._current_position_index = 0

        self._scan_task = asyncio.create_task(self._raster_scan_loop())
        logger.info(
            f"Raster scan started: {len(self._scan_positions)} positions, "
            f"model={model_type}, conf={detection_confidence}"
        )

    async def stop_scan(self):
        """Stop the automated scanning loop."""
        if self._scan_task and not self._scan_task.done():
            self._scan_task.cancel()
            try:
                await self._scan_task
            except asyncio.CancelledError:
                pass

        # Return servos to center position
        try:
            await self.esp32.motor_center()
        except Exception:
            pass

        await self._set_state(ScanState.IDLE, {"reason": "stopped_by_user"})
        logger.info("Auto-scan stopped")

    async def manual_detect(self) -> List[dict]:
        """Capture a frame and run YOLO detection (single shot, no auto-scan)."""
        if not self.esp32.is_connected:
            raise ConnectionError("ESP32-CAM not connected")

        image_bytes = await self.esp32.capture_still()
        detections = self.yolo.detect(image_bytes)
        return [d.to_dict() for d in detections]

    async def manual_classify(self, model_type: str = "mobilenet") -> dict:
        """Capture still, classify disease, and get RAG advice (single shot)."""
        if not self.esp32.is_connected:
            raise ConnectionError("ESP32-CAM not connected")

        image_bytes = await self.esp32.capture_still()

        # Run disease classification
        result = self.classify(image_bytes, model_type=model_type)

        # Get RAG advice if disease detected
        advice = None
        disease_name = result.get("class", "")
        if disease_name and disease_name.lower() != "healthy":
            try:
                weather_condition = None
                weather_forecast = None
                if self.get_weather:
                    weather_condition, weather_forecast = self.get_weather()
                advice = self.get_advice(
                    disease_name,
                    weather_condition=weather_condition,
                    weather_forecast=weather_forecast,
                )
            except Exception as e:
                logger.error(f"RAG advice failed: {e}")

        return {
            "classification": result,
            "advice": advice,
            "image_base64": base64.b64encode(image_bytes).decode("utf-8"),
            "timestamp": datetime.utcnow().isoformat(),
        }

    # =========================================================================
    # Raster Scan Loop
    # =========================================================================

    async def _raster_scan_loop(self):
        """Core raster scan loop: move to position, settle, capture, detect, classify if needed."""
        try:
            await self._set_state(ScanState.SCANNING)

            # Move to starting position
            start_pan, start_tilt = self._scan_positions[0]
            await self.esp32.set_position(start_pan, start_tilt)
            await asyncio.sleep(1.0)  # Initial settle

            while self._current_position_index < len(self._scan_positions):
                pan, tilt = self._scan_positions[self._current_position_index]

                # 1. Move to position
                await self.esp32.set_position(pan, tilt)
                await asyncio.sleep(self._settle_delay)

                # 2. Capture frame
                try:
                    frame_bytes = await self.esp32.capture_still()
                except Exception as e:
                    logger.error(f"Capture failed at ({pan}, {tilt}): {e}")
                    self._current_position_index += 1
                    continue

                # 3. Run YOLO detection
                try:
                    detections = self.yolo.detect(frame_bytes)
                except Exception as e:
                    logger.error(f"YOLO detection error: {e}")
                    self._current_position_index += 1
                    continue

                # 4. Broadcast position + detections
                frame_b64 = base64.b64encode(frame_bytes).decode("utf-8")
                await self._broadcast(ScanEvent(
                    event_type="frame",
                    state=self.state.value,
                    data={
                        "frame_base64": frame_b64,
                        "detections": [d.to_dict() for d in detections],
                        "position": {"pan": pan, "tilt": tilt},
                        "progress": f"{self._current_position_index + 1}/{len(self._scan_positions)}",
                    },
                ))

                # 5. If leaf detected with sufficient confidence, classify
                if detections:
                    best = max(detections, key=lambda d: d.confidence)
                    if best.confidence >= self._detection_confidence:
                        await self._process_detection(detections, pan, tilt, frame_bytes)

                        # Resume scanning state after processing
                        if self.state != ScanState.ERROR:
                            await self._set_state(ScanState.SCANNING)

                self._current_position_index += 1
                await asyncio.sleep(0.1)

            # Scan complete
            await self._set_state(ScanState.IDLE, {
                "reason": "scan_complete",
                "total_positions": len(self._scan_positions),
                "detections_found": len(self._results),
            })
            logger.info(f"Raster scan complete: {len(self._results)} detections processed")

        except asyncio.CancelledError:
            logger.info("Raster scan cancelled")
            raise
        except Exception as e:
            logger.error(f"Raster scan error: {e}", exc_info=True)
            await self._set_state(ScanState.ERROR, {"message": str(e)})
        finally:
            # Return to center position
            try:
                await self.esp32.motor_center()
            except Exception:
                pass

    async def _process_detection(self, detections: list, pan: int, tilt: int, image_bytes: bytes):
        """Handle a leaf detection: classify disease, get RAG advice, store result."""
        self._scan_index += 1
        detection_dicts = [d.to_dict() for d in detections]

        # 1. Leaf detected
        await self._set_state(ScanState.LEAF_DETECTED, {
            "detections": detection_dicts,
            "scan_index": self._scan_index,
            "position": {"pan": pan, "tilt": tilt},
        })

        image_b64 = base64.b64encode(image_bytes).decode("utf-8")

        # 2. Disease classification
        await self._set_state(ScanState.CLASSIFYING)
        try:
            classification = self.classify(image_bytes, model_type=self._model_type)
        except Exception as e:
            logger.error(f"Classification failed: {e}")
            await self._set_state(ScanState.ERROR, {"message": f"Classification failed: {e}"})
            return

        disease = classification.get("class", "Unknown")
        confidence = classification.get("confidence", 0.0)

        await self._broadcast(ScanEvent(
            event_type="classification",
            state=ScanState.CLASSIFYING.value,
            data={
                "disease": disease,
                "confidence": confidence,
                "model": self._model_type,
                "all_predictions": classification.get("all_predictions"),
                "inference_time_ms": classification.get("inference_time_ms"),
                "scan_index": self._scan_index,
                "position": {"pan": pan, "tilt": tilt},
            },
        ))

        # 3. Get RAG advice (skip for healthy plants)
        advice = None
        if disease.lower() != "healthy":
            await self._set_state(ScanState.ADVISING)
            try:
                weather_condition = None
                weather_forecast = None
                if self.get_weather:
                    weather_condition, weather_forecast = self.get_weather()
                advice = self.get_advice(
                    disease,
                    weather_condition=weather_condition,
                    weather_forecast=weather_forecast,
                )
            except Exception as e:
                logger.error(f"RAG advice failed: {e}")
                advice = {"severity": "Unknown", "action_plan": "Advice unavailable", "rag_enabled": False}

        # 4. Store and broadcast result
        result = ScanResult(
            scan_index=self._scan_index,
            detections=detection_dicts,
            disease=disease,
            disease_confidence=confidence,
            classification_model=self._model_type,
            all_predictions=classification.get("all_predictions"),
            advice=advice,
            image_base64=image_b64,
        )
        self._results.append(result)

        await self._set_state(ScanState.RESULT_READY, {
            "result": result.to_dict(),
            "position": {"pan": pan, "tilt": tilt},
        })

        await self._broadcast(ScanEvent(
            event_type="advice",
            state=ScanState.RESULT_READY.value,
            data={
                "disease": disease,
                "confidence": confidence,
                "advice": advice,
                "scan_index": self._scan_index,
                "position": {"pan": pan, "tilt": tilt},
                "image_base64": image_b64,
            },
        ))

        logger.info(
            f"Scan #{self._scan_index} at ({pan}, {tilt}): {disease} ({confidence:.2%}) | "
            f"Advice: {'Yes' if advice else 'Skipped (healthy)'}"
        )

        # Brief pause before resuming
        await asyncio.sleep(1.0)
