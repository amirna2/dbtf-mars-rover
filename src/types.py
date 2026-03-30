"""Data types for the Mars rover controller.

All types are immutable dataclasses. Data flows through function
parameters and return values — no shared mutable state.
"""

from dataclasses import dataclass
from enum import Enum


# --- Sensor Inputs ---

@dataclass(frozen=True)
class HazCamFrame:
    """Raw hazard camera frame."""
    pixels: tuple[tuple[int, ...], ...]  # grayscale grid
    timestamp: float


@dataclass(frozen=True)
class NavCamFrame:
    """Raw navigation camera frame."""
    pixels: tuple[tuple[int, ...], ...]
    timestamp: float


@dataclass(frozen=True)
class IMUReading:
    """Raw inertial measurement unit reading."""
    accel_x: float
    accel_y: float
    accel_z: float
    gyro_x: float
    gyro_y: float
    gyro_z: float
    timestamp: float


@dataclass(frozen=True)
class SensorInputs:
    """Bundle of all raw sensor inputs for one control cycle."""
    hazcam: HazCamFrame
    navcam: NavCamFrame
    imu: IMUReading


# --- Processed Sensor Data ---

@dataclass(frozen=True)
class Obstacle:
    """A detected obstacle in rover-relative coordinates."""
    x: float
    y: float
    radius: float


@dataclass(frozen=True)
class HazardMap:
    """Processed hazard detections from HazCam."""
    obstacles: tuple[Obstacle, ...]
    hazard_detected: bool
    timestamp: float


@dataclass(frozen=True)
class TerrainMap:
    """Processed terrain model from NavCam."""
    traversability: tuple[tuple[float, ...], ...]  # 0.0=impassable, 1.0=clear
    timestamp: float


@dataclass(frozen=True)
class Pose:
    """Estimated rover position and orientation from IMU."""
    x: float
    y: float
    heading: float  # radians
    timestamp: float


# --- World Model ---

@dataclass(frozen=True)
class WorldModel:
    """Fused situational awareness from all sensors."""
    hazard_map: HazardMap
    terrain_map: TerrainMap
    pose: Pose
    hazard_detected: bool


# --- Mission ---

class MissionPhase(Enum):
    TRAVERSE = "traverse"
    SAMPLE = "sample"
    SAFE_HOLD = "safe_hold"


@dataclass(frozen=True)
class Waypoint:
    """A target location for navigation."""
    x: float
    y: float


@dataclass(frozen=True)
class MissionCommand:
    """Current mission command from Earth or autonomy planner."""
    phase: MissionPhase
    waypoint: Waypoint | None = None


# --- Actuator Output ---

class MotionType(Enum):
    HALT = "halt"
    DRIVE = "drive"
    TURN = "turn"
    ARM_SAMPLE = "arm_sample"


@dataclass(frozen=True)
class ActuatorCommand:
    """Command to wheels/arm."""
    motion: MotionType
    speed: float = 0.0       # m/s for drive, rad/s for turn
    duration: float = 0.0    # seconds


# --- Telemetry ---

@dataclass(frozen=True)
class Telemetry:
    """Status report for uplink to Earth."""
    pose: Pose
    hazard_detected: bool
    mission_phase: MissionPhase
    actuator_cmd: ActuatorCommand
