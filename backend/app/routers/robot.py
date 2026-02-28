from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
import httpx
import asyncio
from typing import Optional

router = APIRouter(prefix="/api/robot", tags=["Robot Control"])

# Configuration - Update with your ESP32's IP
ESP32_BASE_URL = "http://192.168.1.100"  # Change to your ESP32 IP
TIMEOUT = 5.0

# --- Models ---
class LinearMotionRequest(BaseModel):
    """Control linear rail movement (rack & pinion / belt drive)"""
    direction: str = Field(..., pattern="^(left|right|stop)$", description="Direction: left, right, or stop")
    speed: int = Field(default=150, ge=0, le=255, description="Motor speed (0-255)")
    steps: Optional[int] = Field(default=None, ge=0, description="Number of steps (for stepper motor). None = continuous")

class PanTiltRequest(BaseModel):
    """Control pan-tilt bracket"""
    pan: Optional[int] = Field(default=None, ge=0, le=180, description="Pan angle (0-180 degrees, 90=center)")
    tilt: Optional[int] = Field(default=None, ge=0, le=180, description="Tilt angle (0-180 degrees, 90=center)")

class PanTiltIncrementRequest(BaseModel):
    """Incremental pan-tilt adjustment"""
    axis: str = Field(..., pattern="^(pan|tilt)$", description="Axis to adjust")
    direction: str = Field(..., pattern="^(positive|negative)$", description="Direction of increment")
    increment: int = Field(default=5, ge=1, le=45, description="Degrees to increment")

class RobotMovementRequest(BaseModel):
    """Legacy robot movement (wheels)"""
    direction: str = Field(..., pattern="^(forward|backward|left|right|stop)$")
    speed: int = Field(default=150, ge=0, le=255)

class HomeRequest(BaseModel):
    """Home the linear rail and/or pan-tilt"""
    home_rail: bool = Field(default=True, description="Home the linear rail to center")
    home_pan_tilt: bool = Field(default=True, description="Home pan-tilt to center (90, 90)")

class CameraPositionPreset(BaseModel):
    """Move to a preset camera position"""
    preset: str = Field(..., pattern="^(home|left_scan|right_scan|top_view|bottom_view|full_left|full_right)$")

# --- State tracking ---
current_state = {
    "linear_position": 50,  # percentage 0-100 (estimated)
    "pan_angle": 90,
    "tilt_angle": 90,
    "rail_moving": False,
    "rail_direction": "stop",
    "rail_speed": 0,
    "connected": False,
}

# --- Presets ---
POSITION_PRESETS = {
    "home": {"pan": 90, "tilt": 90, "rail_direction": "stop"},
    "left_scan": {"pan": 45, "tilt": 90, "rail_direction": "left"},
    "right_scan": {"pan": 135, "tilt": 90, "rail_direction": "right"},
    "top_view": {"pan": 90, "tilt": 45},
    "bottom_view": {"pan": 90, "tilt": 135},
    "full_left": {"pan": 0, "tilt": 90},
    "full_right": {"pan": 180, "tilt": 90},
}

# --- Helper to send commands to ESP32 ---
async def send_esp32_command(endpoint: str, params: dict = None) -> dict:
    """Send command to ESP32 via HTTP"""
    try:
        async with httpx.AsyncClient(timeout=TIMEOUT) as client:
            url = f"{ESP32_BASE_URL}{endpoint}"
            response = await client.get(url, params=params)
            current_state["connected"] = True
            if response.status_code == 200:
                return {"success": True, "data": response.text}
            else:
                return {"success": False, "error": f"ESP32 returned {response.status_code}"}
    except httpx.ConnectError:
        current_state["connected"] = False
        return {"success": False, "error": "Cannot connect to ESP32. Check IP and network."}
    except httpx.TimeoutException:
        current_state["connected"] = False
        return {"success": False, "error": "ESP32 request timed out."}
    except Exception as e:
        return {"success": False, "error": str(e)}

# --- Endpoints ---

@router.get("/status")
async def get_robot_status():
    """Get current robot/camera position status"""
    # Ping ESP32 to check connection
    result = await send_esp32_command("/ping")
    current_state["connected"] = result.get("success", False)
    return {
        "status": "ok",
        "state": current_state,
    }

@router.post("/linear/move")
async def linear_move(request: LinearMotionRequest):
    """Control linear rail movement (rack & pinion / belt drive system)"""
    params = {"dir": request.direction, "speed": request.speed}
    if request.steps is not None:
        params["steps"] = request.steps

    result = await send_esp32_command("/linear", params)

    # Update local state
    current_state["rail_moving"] = request.direction != "stop"
    current_state["rail_direction"] = request.direction
    current_state["rail_speed"] = request.speed if request.direction != "stop" else 0

    if request.direction == "left":
        current_state["linear_position"] = max(0, current_state["linear_position"] - 5)
    elif request.direction == "right":
        current_state["linear_position"] = min(100, current_state["linear_position"] + 5)

    return {
        "message": f"Linear rail: {request.direction} at speed {request.speed}",
        "esp32_response": result,
        "state": current_state,
    }

@router.post("/linear/stop")
async def linear_stop():
    """Emergency stop for linear rail"""
    result = await send_esp32_command("/linear", {"dir": "stop", "speed": 0})
    current_state["rail_moving"] = False
    current_state["rail_direction"] = "stop"
    current_state["rail_speed"] = 0
    return {"message": "Linear rail stopped", "esp32_response": result, "state": current_state}

@router.post("/pantilt/set")
async def pantilt_set(request: PanTiltRequest):
    """Set pan-tilt bracket to specific angles"""
    params = {}
    if request.pan is not None:
        params["pan"] = request.pan
        current_state["pan_angle"] = request.pan
    if request.tilt is not None:
        params["tilt"] = request.tilt
        current_state["tilt_angle"] = request.tilt

    if not params:
        raise HTTPException(status_code=400, detail="Provide at least pan or tilt angle")

    result = await send_esp32_command("/pantilt", params)
    return {
        "message": f"Pan-tilt set to pan={current_state['pan_angle']}°, tilt={current_state['tilt_angle']}°",
        "esp32_response": result,
        "state": current_state,
    }

@router.post("/pantilt/increment")
async def pantilt_increment(request: PanTiltIncrementRequest):
    """Incrementally adjust pan or tilt"""
    delta = request.increment if request.direction == "positive" else -request.increment

    if request.axis == "pan":
        new_angle = max(0, min(180, current_state["pan_angle"] + delta))
        current_state["pan_angle"] = new_angle
        params = {"pan": new_angle, "tilt": current_state["tilt_angle"]}
    else:
        new_angle = max(0, min(180, current_state["tilt_angle"] + delta))
        current_state["tilt_angle"] = new_angle
        params = {"pan": current_state["pan_angle"], "tilt": new_angle}

    result = await send_esp32_command("/pantilt", params)
    return {
        "message": f"{request.axis} adjusted by {delta}° to {new_angle}°",
        "esp32_response": result,
        "state": current_state,
    }

@router.post("/pantilt/home")
async def pantilt_home():
    """Center pan-tilt bracket to home position (90, 90)"""
    current_state["pan_angle"] = 90
    current_state["tilt_angle"] = 90
    result = await send_esp32_command("/pantilt", {"pan": 90, "tilt": 90})
    return {"message": "Pan-tilt homed to center (90°, 90°)", "esp32_response": result, "state": current_state}

@router.post("/home")
async def home_all(request: HomeRequest):
    """Home linear rail and/or pan-tilt to default positions"""
    results = {}

    if request.home_pan_tilt:
        current_state["pan_angle"] = 90
        current_state["tilt_angle"] = 90
        results["pantilt"] = await send_esp32_command("/pantilt", {"pan": 90, "tilt": 90})

    if request.home_rail:
        current_state["rail_moving"] = False
        current_state["rail_direction"] = "stop"
        current_state["rail_speed"] = 0
        current_state["linear_position"] = 50
        results["rail"] = await send_esp32_command("/home")

    return {"message": "System homed", "results": results, "state": current_state}

@router.post("/preset")
async def move_to_preset(request: CameraPositionPreset):
    """Move camera to a preset position"""
    preset = POSITION_PRESETS.get(request.preset)
    if not preset:
        raise HTTPException(status_code=400, detail="Invalid preset")

    results = {}

    if "pan" in preset or "tilt" in preset:
        pan = preset.get("pan", current_state["pan_angle"])
        tilt = preset.get("tilt", current_state["tilt_angle"])
        current_state["pan_angle"] = pan
        current_state["tilt_angle"] = tilt
        results["pantilt"] = await send_esp32_command("/pantilt", {"pan": pan, "tilt": tilt})

    if "rail_direction" in preset:
        direction = preset["rail_direction"]
        current_state["rail_direction"] = direction
        current_state["rail_moving"] = direction != "stop"
        results["rail"] = await send_esp32_command("/linear", {"dir": direction, "speed": 150})

    return {
        "message": f"Moved to preset: {request.preset}",
        "results": results,
        "state": current_state,
    }

@router.post("/move")
async def move_robot(request: RobotMovementRequest):
    """Legacy: Move robot wheels (if applicable)"""
    result = await send_esp32_command("/move", {"dir": request.direction, "speed": request.speed})
    return {"message": f"Robot moving {request.direction}", "esp32_response": result}

@router.get("/stream-url")
async def get_stream_url():
    """Get ESP32-CAM stream URL"""
    return {
        "stream_url": f"{ESP32_BASE_URL}:81/stream",
        "snapshot_url": f"{ESP32_BASE_URL}/capture",
        "connected": current_state["connected"],
    }
