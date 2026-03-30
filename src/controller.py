"""Mars rover autonomy controller.

Implements the MissionStep control loop: read sensors, fuse state,
plan action, safety check, build telemetry.
"""

import math

from src.types import (
    ActuatorCommand,
    HazardMap,
    HazCamFrame,
    IMUReading,
    MissionCommand,
    MissionPhase,
    MotionType,
    NavCamFrame,
    Obstacle,
    Pose,
    SensorInputs,
    Telemetry,
    TerrainMap,
    Waypoint,
    WorldModel,
)


class SensorError(Exception):
    """Raised when sensor data is invalid (Axiom 5 — domain rejection)."""


class PlannerError(Exception):
    """Raised when mission command is invalid (Axiom 5 — domain rejection)."""


# ---------------------------------------------------------------------------
# MissionStep — Top-level Join
#
#   step(sensors, mission_cmd) = (actuator_cmd, telemetry)
#    |-- read_sensors(sensors) = (hazard_map, terrain_map, pose)
#    |-- fuse_state(hazard_map, terrain_map, pose) = world_model
#    |-- plan_action(world_model, mission_cmd) = planned_cmd
#    |-- safety_check(world_model, planned_cmd) = actuator_cmd
#    '-- build_telemetry(world_model, actuator_cmd, mission_cmd) = telemetry
# ---------------------------------------------------------------------------

def step(
    sensors: SensorInputs,
    mission_cmd: MissionCommand,
) -> tuple[ActuatorCommand, Telemetry]:
    """Execute one control cycle. Join: each child depends on the previous."""
    hazard_map, terrain_map, pose = read_sensors(sensors)
    world_model = fuse_state(hazard_map, terrain_map, pose)
    planned_cmd = plan_action(world_model, mission_cmd)
    actuator_cmd = safety_check(world_model, planned_cmd)
    telemetry = build_telemetry(world_model, actuator_cmd, mission_cmd)
    return actuator_cmd, telemetry


# ---------------------------------------------------------------------------
# ReadSensors — Include (independent children)
#
#   read_sensors(sensors) = (hazard_map, terrain_map, pose)
#    |-- process_hazcam(sensors.hazcam) = hazard_map    [independent]
#    |-- process_navcam(sensors.navcam) = terrain_map   [independent]
#    '-- process_imu(sensors.imu) = pose                [independent]
# ---------------------------------------------------------------------------

def read_sensors(
    sensors: SensorInputs,
) -> tuple[HazardMap, TerrainMap, Pose]:
    """Include: three independent sensor processors. No shared state."""
    hazard_map = process_hazcam(sensors.hazcam)
    terrain_map = process_navcam(sensors.navcam)
    pose = process_imu(sensors.imu)
    return hazard_map, terrain_map, pose


def process_hazcam(frame: HazCamFrame) -> HazardMap:
    """Process raw HazCam frame into obstacle detections."""
    # Axiom 5: reject invalid input.
    if not frame.pixels:
        raise SensorError("HazCam frame has no pixel data")
    if frame.timestamp < 0:
        raise SensorError(f"HazCam timestamp invalid: {frame.timestamp}")

    # Simple obstacle detection: any pixel above threshold is an obstacle.
    obstacles = []
    rows = len(frame.pixels)
    cols = len(frame.pixels[0]) if rows > 0 else 0
    for r in range(rows):
        for c in range(cols):
            if frame.pixels[r][c] > 200:
                # Convert pixel position to rover-relative coords.
                x = (c - cols / 2) * 0.1
                y = (rows - r) * 0.1
                obstacles.append(Obstacle(x=x, y=y, radius=0.3))

    return HazardMap(
        obstacles=tuple(obstacles),
        hazard_detected=len(obstacles) > 0,
        timestamp=frame.timestamp,
    )


def process_navcam(frame: NavCamFrame) -> TerrainMap:
    """Process raw NavCam frame into terrain traversability grid."""
    # Axiom 5: reject invalid input.
    if not frame.pixels:
        raise SensorError("NavCam frame has no pixel data")
    if frame.timestamp < 0:
        raise SensorError(f"NavCam timestamp invalid: {frame.timestamp}")

    # Simple traversability: normalize pixel values to 0.0-1.0.
    traversability = tuple(
        tuple(min(p / 255.0, 1.0) for p in row)
        for row in frame.pixels
    )
    return TerrainMap(traversability=traversability, timestamp=frame.timestamp)


def process_imu(reading: IMUReading) -> Pose:
    """Process raw IMU reading into pose estimate."""
    # Axiom 5: reject invalid input.
    if reading.timestamp < 0:
        raise SensorError(f"IMU timestamp invalid: {reading.timestamp}")

    # Simplified: derive heading from gyro, position from accel.
    heading = math.atan2(reading.gyro_y, reading.gyro_x)
    x = reading.accel_x
    y = reading.accel_y
    return Pose(x=x, y=y, heading=heading, timestamp=reading.timestamp)


# ---------------------------------------------------------------------------
# FuseState — Join (single child, leaf node)
#
#   fuse_state(hazard_map, terrain_map, pose) = world_model
# ---------------------------------------------------------------------------

def fuse_state(
    hazard_map: HazardMap,
    terrain_map: TerrainMap,
    pose: Pose,
) -> WorldModel:
    """Fuse sensor data into a unified world model."""
    return WorldModel(
        hazard_map=hazard_map,
        terrain_map=terrain_map,
        pose=pose,
        hazard_detected=hazard_map.hazard_detected,
    )


# ---------------------------------------------------------------------------
# PlanAction — Or (decision: exactly one branch executes)
#
#   plan_action(world_model, mission_cmd) = planned_cmd
#    |-- [phase == TRAVERSE]  -> plan_traverse(world_model, mission_cmd) = planned_cmd
#    |-- [phase == SAMPLE]    -> plan_sample(world_model, mission_cmd) = planned_cmd
#    '-- [phase == SAFE_HOLD] -> hold_position(world_model) = planned_cmd
# ---------------------------------------------------------------------------

def plan_action(
    world_model: WorldModel,
    mission_cmd: MissionCommand,
) -> ActuatorCommand:
    """Or: select planner based on mission phase."""
    # Axiom 5: reject invalid input.
    if not isinstance(mission_cmd.phase, MissionPhase):
        raise PlannerError(f"Unknown mission phase: {mission_cmd.phase}")

    if mission_cmd.phase == MissionPhase.TRAVERSE:
        return plan_traverse(world_model, mission_cmd)
    elif mission_cmd.phase == MissionPhase.SAMPLE:
        return plan_sample(world_model, mission_cmd)
    elif mission_cmd.phase == MissionPhase.SAFE_HOLD:
        return hold_position(world_model)

    # Axiom 5: exhaustive — no silent fallthrough.
    raise PlannerError(f"Unhandled mission phase: {mission_cmd.phase}")


def plan_traverse(
    world_model: WorldModel,
    mission_cmd: MissionCommand,
) -> ActuatorCommand:
    """Plan movement toward waypoint."""
    if mission_cmd.waypoint is None:
        raise PlannerError("TRAVERSE phase requires a waypoint")

    waypoint = mission_cmd.waypoint
    pose = world_model.pose

    # Calculate heading to waypoint.
    dx = waypoint.x - pose.x
    dy = waypoint.y - pose.y
    target_heading = math.atan2(dy, dx)
    heading_error = target_heading - pose.heading

    # Normalize to [-pi, pi].
    heading_error = (heading_error + math.pi) % (2 * math.pi) - math.pi

    # If heading error is large, turn first. Otherwise drive.
    if abs(heading_error) > 0.1:
        return ActuatorCommand(
            motion=MotionType.TURN,
            speed=0.5 if heading_error > 0 else -0.5,
            duration=abs(heading_error) / 0.5,
        )

    distance = math.sqrt(dx * dx + dy * dy)
    if distance < 0.1:
        return ActuatorCommand(motion=MotionType.HALT)

    return ActuatorCommand(
        motion=MotionType.DRIVE,
        speed=min(0.5, distance),
        duration=min(distance / 0.5, 2.0),
    )


def plan_sample(
    world_model: WorldModel,
    mission_cmd: MissionCommand,
) -> ActuatorCommand:
    """Plan soil sample collection."""
    return ActuatorCommand(motion=MotionType.ARM_SAMPLE, duration=5.0)


def hold_position(world_model: WorldModel) -> ActuatorCommand:
    """Hold current position — safe hold mode."""
    return ActuatorCommand(motion=MotionType.HALT)


# ---------------------------------------------------------------------------
# SafetyCheck — Or (decision: hazard overrides planned command)
#
#   safety_check(world_model, planned_cmd) = actuator_cmd
#    |-- [hazard_detected == true]  -> emergency_stop(world_model) = actuator_cmd
#    '-- [hazard_detected == false] -> pass_through(planned_cmd) = actuator_cmd
# ---------------------------------------------------------------------------

def safety_check(
    world_model: WorldModel,
    planned_cmd: ActuatorCommand,
) -> ActuatorCommand:
    """Or: hazard detected triggers emergency stop, otherwise pass through."""
    if world_model.hazard_detected:
        return emergency_stop(world_model)
    else:
        return pass_through(planned_cmd)


def emergency_stop(world_model: WorldModel) -> ActuatorCommand:
    """Halt all motion — hazard detected."""
    return ActuatorCommand(motion=MotionType.HALT)


def pass_through(planned_cmd: ActuatorCommand) -> ActuatorCommand:
    """Forward planned command to actuators — no hazard."""
    return planned_cmd


# ---------------------------------------------------------------------------
# BuildTelemetry — leaf node
#
#   build_telemetry(world_model, actuator_cmd, mission_cmd) = telemetry
# ---------------------------------------------------------------------------

def build_telemetry(
    world_model: WorldModel,
    actuator_cmd: ActuatorCommand,
    mission_cmd: MissionCommand,
) -> Telemetry:
    """Build telemetry report for uplink."""
    return Telemetry(
        pose=world_model.pose,
        hazard_detected=world_model.hazard_detected,
        mission_phase=mission_cmd.phase,
        actuator_cmd=actuator_cmd,
    )
