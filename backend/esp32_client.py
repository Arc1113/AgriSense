"""
AgriSense ESP32-CAM Client - Async HTTP Communication

Communicates with an ESP32-CAM device over WiFi.
Handles MJPEG stream consumption, pan-tilt servo control, and still image capture.

Expected ESP32-CAM HTTP endpoints:
  GET  /stream                    -> MJPEG video stream (multipart/x-mixed-replace)
  GET  /capture                   -> Single JPEG still (high resolution)
  GET  /status                    -> JSON: {"pan_angle": 90, "tilt_angle": 75, "camera": true, ...}
  POST /motor/left?step=5         -> Pan servo left by N degrees
  POST /motor/right?step=5        -> Pan servo right by N degrees
  POST /motor/up?step=5           -> Tilt servo up by N degrees
  POST /motor/down?step=5         -> Tilt servo down by N degrees
  POST /motor/center              -> Center both servos
  POST /motor/stop                -> No-op (compatibility), report position
  POST /motor/position?pan=N&tilt=N -> Set absolute servo positions
  GET  /motor/position            -> Get current servo angles
"""

import logging
import asyncio
from typing import Optional, AsyncIterator, Dict, Any

import httpx

logger = logging.getLogger("AgriSense.ESP32")


class ESP32Client:
    """Async HTTP client for ESP32-CAM communication."""

    def __init__(self, base_url: str = None):
        self._base_url: Optional[str] = base_url
        self._client: Optional[httpx.AsyncClient] = None
        self._connected: bool = False
        self._timeout = httpx.Timeout(connect=5.0, read=10.0, write=5.0, pool=5.0)

    async def connect(self, ip_address: str, port: int = 80) -> bool:
        """Connect to an ESP32-CAM device by IP address."""
        self._base_url = f"http://{ip_address}:{port}"

        # Close existing client if any
        if self._client:
            await self._client.aclose()

        self._client = httpx.AsyncClient(timeout=self._timeout)

        try:
            response = await self._client.get(f"{self._base_url}/status")
            if response.status_code == 200:
                self._connected = True
                logger.info(f"Connected to ESP32-CAM at {self._base_url}")
                return True
            else:
                logger.warning(f"ESP32-CAM responded with status {response.status_code}")
                self._connected = False
                return False
        except httpx.ConnectError:
            logger.error(f"Cannot reach ESP32-CAM at {self._base_url}")
            self._connected = False
            return False
        except httpx.TimeoutException:
            logger.error(f"Timeout connecting to ESP32-CAM at {self._base_url}")
            self._connected = False
            return False
        except Exception as e:
            logger.error(f"ESP32-CAM connection error: {e}")
            self._connected = False
            return False

    async def disconnect(self):
        """Disconnect from ESP32-CAM."""
        if self._client:
            await self._client.aclose()
            self._client = None
        self._connected = False
        logger.info("Disconnected from ESP32-CAM")

    @property
    def is_connected(self) -> bool:
        return self._connected

    @property
    def base_url(self) -> Optional[str]:
        return self._base_url

    def _ensure_connected(self):
        if not self._connected or not self._client:
            raise ConnectionError("Not connected to ESP32-CAM. Call connect() first.")

    # =========================================================================
    # Motor Control
    # =========================================================================

    async def motor_left(self, step: int = 5) -> bool:
        """Command pan servo to step left (counter-clockwise)."""
        self._ensure_connected()
        try:
            resp = await self._client.post(
                f"{self._base_url}/motor/left", params={"step": step}
            )
            ok = resp.status_code == 200
            if ok:
                logger.info(f"Pan stepping LEFT by {step} degrees")
            return ok
        except Exception as e:
            logger.error(f"Motor left command failed: {e}")
            return False

    async def motor_right(self, step: int = 5) -> bool:
        """Command pan servo to step right (clockwise)."""
        self._ensure_connected()
        try:
            resp = await self._client.post(
                f"{self._base_url}/motor/right", params={"step": step}
            )
            ok = resp.status_code == 200
            if ok:
                logger.info(f"Pan stepping RIGHT by {step} degrees")
            return ok
        except Exception as e:
            logger.error(f"Motor right command failed: {e}")
            return False

    async def motor_stop(self) -> bool:
        """Command servos to hold current position (compatibility)."""
        self._ensure_connected()
        try:
            resp = await self._client.post(f"{self._base_url}/motor/stop")
            ok = resp.status_code == 200
            if ok:
                logger.info("Servos holding position")
            return ok
        except Exception as e:
            logger.error(f"Motor stop command failed: {e}")
            return False

    async def motor_up(self, step: int = 5) -> bool:
        """Command tilt servo to step up."""
        self._ensure_connected()
        try:
            resp = await self._client.post(
                f"{self._base_url}/motor/up", params={"step": step}
            )
            ok = resp.status_code == 200
            if ok:
                logger.info(f"Tilt stepping UP by {step} degrees")
            return ok
        except Exception as e:
            logger.error(f"Motor up command failed: {e}")
            return False

    async def motor_down(self, step: int = 5) -> bool:
        """Command tilt servo to step down."""
        self._ensure_connected()
        try:
            resp = await self._client.post(
                f"{self._base_url}/motor/down", params={"step": step}
            )
            ok = resp.status_code == 200
            if ok:
                logger.info(f"Tilt stepping DOWN by {step} degrees")
            return ok
        except Exception as e:
            logger.error(f"Motor down command failed: {e}")
            return False

    async def motor_center(self) -> bool:
        """Command both servos to return to center position."""
        self._ensure_connected()
        try:
            resp = await self._client.post(f"{self._base_url}/motor/center")
            ok = resp.status_code == 200
            if ok:
                logger.info("Servos returning to CENTER")
            return ok
        except Exception as e:
            logger.error(f"Motor center command failed: {e}")
            return False

    async def set_position(self, pan: int, tilt: int) -> bool:
        """Set absolute servo positions (degrees)."""
        self._ensure_connected()
        try:
            resp = await self._client.post(
                f"{self._base_url}/motor/position",
                params={"pan": pan, "tilt": tilt},
            )
            ok = resp.status_code == 200
            if ok:
                logger.info(f"Servos positioned: pan={pan}, tilt={tilt}")
            return ok
        except Exception as e:
            logger.error(f"Set position command failed: {e}")
            return False

    async def get_position(self) -> Dict[str, int]:
        """Get current servo positions."""
        self._ensure_connected()
        try:
            resp = await self._client.get(f"{self._base_url}/motor/position")
            if resp.status_code == 200:
                return resp.json()
            return {"pan_angle": 90, "tilt_angle": 75}
        except Exception as e:
            logger.error(f"Get position failed: {e}")
            return {"pan_angle": 90, "tilt_angle": 75}

    # =========================================================================
    # Camera
    # =========================================================================

    async def capture_still(self) -> bytes:
        """Capture a single high-resolution still image from ESP32-CAM."""
        self._ensure_connected()
        try:
            resp = await self._client.get(
                f"{self._base_url}/capture",
                timeout=httpx.Timeout(connect=5.0, read=15.0, write=5.0, pool=5.0),
            )
            if resp.status_code == 200:
                logger.info(f"Captured still image: {len(resp.content)} bytes")
                return resp.content
            else:
                raise RuntimeError(f"Capture failed with status {resp.status_code}")
        except httpx.TimeoutException:
            raise RuntimeError("Timeout capturing still image from ESP32-CAM")

    async def stream_frames(self) -> AsyncIterator[bytes]:
        """
        Consume the ESP32-CAM MJPEG stream, yielding individual JPEG frames.

        The ESP32-CAM /stream endpoint emits multipart/x-mixed-replace with
        JPEG frames separated by boundaries. This parser extracts individual
        JPEG frames by finding SOI (0xFFD8) and EOI (0xFFD9) markers.
        """
        self._ensure_connected()

        stream_timeout = httpx.Timeout(connect=5.0, read=30.0, write=5.0, pool=5.0)

        async with self._client.stream(
            "GET", f"{self._base_url}/stream", timeout=stream_timeout
        ) as response:
            buffer = b""
            async for chunk in response.aiter_bytes(chunk_size=4096):
                buffer += chunk
                while True:
                    # Find JPEG start-of-image marker
                    start = buffer.find(b"\xff\xd8")
                    if start == -1:
                        # No SOI found, discard everything before the last byte
                        # (keep last byte in case it's the start of 0xFFD8)
                        if len(buffer) > 1:
                            buffer = buffer[-1:]
                        break

                    # Find JPEG end-of-image marker after SOI
                    end = buffer.find(b"\xff\xd9", start + 2)
                    if end == -1:
                        # No EOI yet, need more data
                        # Discard anything before SOI
                        buffer = buffer[start:]
                        break

                    # Extract complete JPEG frame
                    frame = buffer[start : end + 2]
                    buffer = buffer[end + 2 :]
                    yield frame

    async def proxy_stream(self) -> AsyncIterator[bytes]:
        """
        Proxy the ESP32 MJPEG stream in multipart/x-mixed-replace format.

        Yields raw multipart chunks suitable for a StreamingResponse.
        """
        async for frame in self.stream_frames():
            yield (
                b"--frame\r\n"
                b"Content-Type: image/jpeg\r\n"
                b"Content-Length: " + str(len(frame)).encode() + b"\r\n"
                b"\r\n" + frame + b"\r\n"
            )

    # =========================================================================
    # Status
    # =========================================================================

    async def get_status(self) -> Dict[str, Any]:
        """Get ESP32-CAM device status."""
        self._ensure_connected()
        try:
            resp = await self._client.get(f"{self._base_url}/status")
            if resp.status_code == 200:
                return resp.json()
            return {"error": f"Status request failed: {resp.status_code}"}
        except Exception as e:
            logger.error(f"Status request failed: {e}")
            self._connected = False
            return {"error": str(e), "connected": False}

    async def health_check(self) -> bool:
        """Ping the ESP32-CAM to verify connection is still alive."""
        if not self._client or not self._base_url:
            return False
        try:
            resp = await self._client.get(
                f"{self._base_url}/status",
                timeout=httpx.Timeout(connect=3.0, read=3.0, write=3.0, pool=3.0),
            )
            alive = resp.status_code == 200
            self._connected = alive
            return alive
        except Exception:
            self._connected = False
            return False
