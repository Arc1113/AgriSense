"""
AgriSense YOLO Detector - YOLOv8s Leaf Detection via ONNX Runtime

Detects tomato leaves in images using the YOLOv8s model exported to ONNX format.
Used by the ESP32-CAM robotics scanning pipeline to identify leaves before
disease classification.

Model config from models/YoloV8/model_metadata_v2.json:
- Architecture: YOLOv8s (11M params)
- Input: 640x640x3
- Classes: 1 (Tomato_Leaf)
- Confidence threshold: 0.25
- IoU threshold: 0.6
"""

import os
import json
import logging
import time
from dataclasses import dataclass, asdict
from typing import List, Tuple, Optional

import numpy as np

logger = logging.getLogger("AgriSense.YOLO")

# Lazy import - only loaded when detector is instantiated
ort = None
cv2 = None


def _ensure_imports():
    global ort, cv2
    if ort is None:
        import onnxruntime as _ort
        ort = _ort
    if cv2 is None:
        import cv2 as _cv2
        cv2 = _cv2


@dataclass
class Detection:
    """A single detected object with bounding box coordinates in original image space."""
    x1: float
    y1: float
    x2: float
    y2: float
    confidence: float
    class_name: str = "Tomato_Leaf"

    def to_dict(self) -> dict:
        return asdict(self)


class YOLODetector:
    """YOLOv8s leaf detection using ONNX Runtime."""

    def __init__(
        self,
        model_path: str = None,
        conf_threshold: float = 0.25,
        iou_threshold: float = 0.6,
    ):
        if model_path is None:
            backend_dir = os.path.dirname(os.path.abspath(__file__))
            model_path = os.path.join(backend_dir, "models", "YoloV8", "yolov8s_tomato_leaf.onnx")

        self.model_path = model_path
        self.conf_threshold = conf_threshold
        self.iou_threshold = iou_threshold
        self.input_size = (640, 640)
        self.class_names = ["Tomato_Leaf"]
        self.session: Optional[object] = None
        self._loaded = False

        # Try loading metadata
        metadata_path = os.path.join(os.path.dirname(model_path), "model_metadata_v2.json")
        if os.path.exists(metadata_path):
            try:
                with open(metadata_path, "r") as f:
                    meta = json.load(f)
                self.conf_threshold = meta.get("confidence_threshold", conf_threshold)
                self.iou_threshold = meta.get("iou_threshold", iou_threshold)
                self.class_names = meta.get("class_names", self.class_names)
                input_shape = meta.get("input_shape", [640, 640, 3])
                self.input_size = (input_shape[0], input_shape[1])
                logger.info(f"Loaded YOLO metadata: {meta.get('model_name', 'unknown')}")
            except Exception as e:
                logger.warning(f"Could not load YOLO metadata: {e}")

    def load(self) -> bool:
        """Load the ONNX model into an inference session."""
        _ensure_imports()

        if not os.path.exists(self.model_path):
            logger.error(f"YOLO model not found at: {self.model_path}")
            return False

        try:
            start = time.time()
            providers = ["CPUExecutionProvider"]
            # Try GPU if available
            available = ort.get_available_providers()
            if "CUDAExecutionProvider" in available:
                providers.insert(0, "CUDAExecutionProvider")

            self.session = ort.InferenceSession(self.model_path, providers=providers)
            load_time = (time.time() - start) * 1000

            input_info = self.session.get_inputs()[0]
            output_info = self.session.get_outputs()[0]
            logger.info(
                f"YOLO model loaded in {load_time:.0f}ms | "
                f"Input: {input_info.name} {input_info.shape} | "
                f"Output: {output_info.name} {output_info.shape} | "
                f"Provider: {self.session.get_providers()[0]}"
            )
            self._loaded = True
            return True
        except Exception as e:
            logger.error(f"Failed to load YOLO model: {e}")
            return False

    @property
    def is_loaded(self) -> bool:
        return self._loaded and self.session is not None

    def detect(self, image_bytes: bytes) -> List[Detection]:
        """
        Run leaf detection on raw image bytes (JPEG/PNG).

        Returns list of Detection objects with bounding boxes in original image coordinates.
        """
        if not self.is_loaded:
            raise RuntimeError("YOLO model not loaded. Call load() first.")

        _ensure_imports()

        # Decode image
        nparr = np.frombuffer(image_bytes, np.uint8)
        img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        if img is None:
            raise ValueError("Failed to decode image bytes")

        orig_h, orig_w = img.shape[:2]

        # Preprocess: letterbox resize
        resized, ratio, (pad_w, pad_h) = self._letterbox(img, self.input_size)

        # BGR -> RGB, normalize to [0, 1], NHWC -> NCHW
        blob = resized[:, :, ::-1].astype(np.float32) / 255.0
        blob = np.transpose(blob, (2, 0, 1))  # HWC -> CHW
        blob = np.expand_dims(blob, axis=0)  # Add batch: NCHW

        # Run inference
        input_name = self.session.get_inputs()[0].name
        start = time.time()
        outputs = self.session.run(None, {input_name: blob})
        inference_ms = (time.time() - start) * 1000

        # Post-process
        detections = self._postprocess(outputs[0], ratio, (pad_w, pad_h), orig_w, orig_h)

        logger.info(
            f"YOLO inference: {inference_ms:.1f}ms | "
            f"Detections: {len(detections)} | "
            f"Image: {orig_w}x{orig_h}"
        )

        return detections

    def detect_with_timing(self, image_bytes: bytes) -> Tuple[List[Detection], float]:
        """Run detection and return (detections, inference_time_ms)."""
        if not self.is_loaded:
            raise RuntimeError("YOLO model not loaded. Call load() first.")

        _ensure_imports()
        start = time.time()
        detections = self.detect(image_bytes)
        total_ms = (time.time() - start) * 1000
        return detections, total_ms

    def _letterbox(
        self, img: np.ndarray, new_shape: Tuple[int, int] = (640, 640)
    ) -> Tuple[np.ndarray, float, Tuple[int, int]]:
        """Resize image with letterbox padding (preserve aspect ratio)."""
        h, w = img.shape[:2]
        ratio = min(new_shape[0] / h, new_shape[1] / w)
        new_unpad_h, new_unpad_w = int(round(h * ratio)), int(round(w * ratio))

        pad_w = (new_shape[1] - new_unpad_w) // 2
        pad_h = (new_shape[0] - new_unpad_h) // 2

        if (h, w) != (new_unpad_h, new_unpad_w):
            img = cv2.resize(img, (new_unpad_w, new_unpad_h), interpolation=cv2.INTER_LINEAR)

        # Add padding
        padded = cv2.copyMakeBorder(
            img,
            pad_h, new_shape[0] - new_unpad_h - pad_h,
            pad_w, new_shape[1] - new_unpad_w - pad_w,
            cv2.BORDER_CONSTANT,
            value=(114, 114, 114),
        )

        return padded, ratio, (pad_w, pad_h)

    def _postprocess(
        self,
        output: np.ndarray,
        ratio: float,
        pad: Tuple[int, int],
        orig_w: int,
        orig_h: int,
    ) -> List[Detection]:
        """
        Post-process YOLOv8 ONNX output.

        YOLOv8 output shape is [1, 4+num_classes, num_predictions] = [1, 5, 8400] for 1 class.
        Rows: [cx, cy, w, h, class_conf...]
        """
        # Handle output shape
        if output.ndim == 3:
            output = output[0]  # Remove batch dim -> [5, 8400] or [8400, 5]

        # YOLOv8 exports as [4+C, N], transpose if needed
        if output.shape[0] < output.shape[1]:
            output = output.T  # -> [N, 5]

        num_detections = output.shape[0]
        num_classes = output.shape[1] - 4

        boxes_xywh = output[:, :4]  # cx, cy, w, h
        class_scores = output[:, 4:]  # class confidences

        # For single-class, just take the one score
        if num_classes == 1:
            confidences = class_scores[:, 0]
            class_ids = np.zeros(num_detections, dtype=int)
        else:
            confidences = np.max(class_scores, axis=1)
            class_ids = np.argmax(class_scores, axis=1)

        # Filter by confidence
        mask = confidences >= self.conf_threshold
        boxes_xywh = boxes_xywh[mask]
        confidences = confidences[mask]
        class_ids = class_ids[mask]

        if len(boxes_xywh) == 0:
            return []

        # Convert cx,cy,w,h -> x1,y1,x2,y2
        boxes_xyxy = np.zeros_like(boxes_xywh)
        boxes_xyxy[:, 0] = boxes_xywh[:, 0] - boxes_xywh[:, 2] / 2  # x1
        boxes_xyxy[:, 1] = boxes_xywh[:, 1] - boxes_xywh[:, 3] / 2  # y1
        boxes_xyxy[:, 2] = boxes_xywh[:, 0] + boxes_xywh[:, 2] / 2  # x2
        boxes_xyxy[:, 3] = boxes_xywh[:, 1] + boxes_xywh[:, 3] / 2  # y2

        # Scale boxes back to original image coordinates
        pad_w, pad_h = pad
        boxes_xyxy[:, 0] = (boxes_xyxy[:, 0] - pad_w) / ratio
        boxes_xyxy[:, 1] = (boxes_xyxy[:, 1] - pad_h) / ratio
        boxes_xyxy[:, 2] = (boxes_xyxy[:, 2] - pad_w) / ratio
        boxes_xyxy[:, 3] = (boxes_xyxy[:, 3] - pad_h) / ratio

        # Clip to image boundaries
        boxes_xyxy[:, 0] = np.clip(boxes_xyxy[:, 0], 0, orig_w)
        boxes_xyxy[:, 1] = np.clip(boxes_xyxy[:, 1], 0, orig_h)
        boxes_xyxy[:, 2] = np.clip(boxes_xyxy[:, 2], 0, orig_w)
        boxes_xyxy[:, 3] = np.clip(boxes_xyxy[:, 3], 0, orig_h)

        # Apply NMS
        keep_indices = self._nms(boxes_xyxy, confidences, self.iou_threshold)

        detections = []
        for i in keep_indices:
            cls_id = int(class_ids[i])
            cls_name = self.class_names[cls_id] if cls_id < len(self.class_names) else f"class_{cls_id}"
            detections.append(
                Detection(
                    x1=round(float(boxes_xyxy[i, 0]), 1),
                    y1=round(float(boxes_xyxy[i, 1]), 1),
                    x2=round(float(boxes_xyxy[i, 2]), 1),
                    y2=round(float(boxes_xyxy[i, 3]), 1),
                    confidence=round(float(confidences[i]), 4),
                    class_name=cls_name,
                )
            )

        # Sort by confidence descending
        detections.sort(key=lambda d: d.confidence, reverse=True)
        return detections

    def _nms(
        self, boxes: np.ndarray, scores: np.ndarray, iou_threshold: float
    ) -> List[int]:
        """Non-Maximum Suppression."""
        if len(boxes) == 0:
            return []

        x1 = boxes[:, 0]
        y1 = boxes[:, 1]
        x2 = boxes[:, 2]
        y2 = boxes[:, 3]
        areas = (x2 - x1) * (y2 - y1)

        order = scores.argsort()[::-1]
        keep = []

        while len(order) > 0:
            i = order[0]
            keep.append(i)

            if len(order) == 1:
                break

            xx1 = np.maximum(x1[i], x1[order[1:]])
            yy1 = np.maximum(y1[i], y1[order[1:]])
            xx2 = np.minimum(x2[i], x2[order[1:]])
            yy2 = np.minimum(y2[i], y2[order[1:]])

            inter_w = np.maximum(0, xx2 - xx1)
            inter_h = np.maximum(0, yy2 - yy1)
            intersection = inter_w * inter_h

            union = areas[i] + areas[order[1:]] - intersection
            iou = intersection / (union + 1e-6)

            remaining = np.where(iou <= iou_threshold)[0]
            order = order[remaining + 1]

        return keep
