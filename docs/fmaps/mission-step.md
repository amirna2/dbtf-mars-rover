# FMap: MissionStep — Top-Level Control Loop

> Defined before implementation. The control hierarchy and variable assignments
> are verified against Hamilton's six axioms before any code is written.
>
> Reference: Hamilton & Hackler, "Universal Systems Language for Preventative
> Systems Engineering," CSER 2007.

---

## Variables (Ordered Sets)

### Inputs

| Variable | Type | Description |
|----------|------|-------------|
| `raw_hazcam` | HazCamFrame | Raw hazard camera frame |
| `raw_navcam` | NavCamFrame | Raw navigation camera frame |
| `raw_imu` | IMUReading | Raw inertial measurement unit reading |
| `mission_cmd` | MissionCommand | Current mission command (waypoint, phase) |

### Outputs

| Variable | Type | Description |
|----------|------|-------------|
| `actuator_cmd` | ActuatorCommand | Command to wheels/arm (or halt) |
| `telemetry` | Telemetry | Status report for uplink to Earth |

### Locals

| Variable | Type | Description |
|----------|------|-------------|
| `hazard_map` | HazardMap | Processed hazard detections from HazCam |
| `terrain_map` | TerrainMap | Processed terrain model from NavCam |
| `pose` | Pose | Estimated position + orientation from IMU |
| `world_model` | WorldModel | Fused situational awareness |
| `planned_cmd` | ActuatorCommand | Command from mission planner (before hazard check) |

---

## Structure

```
MissionStep(raw_hazcam, raw_navcam, raw_imu, mission_cmd) = (actuator_cmd, telemetry)

Join [dependent — pipeline]
 |
 |-- ReadSensors(raw_hazcam, raw_navcam, raw_imu) = (hazard_map, terrain_map, pose)
 |
 |-- FuseState(hazard_map, terrain_map, pose) = world_model
 |
 |-- PlanAction(world_model, mission_cmd) = planned_cmd
 |
 |-- SafetyCheck(world_model, planned_cmd) = actuator_cmd
 |
 '-- BuildTelemetry(world_model, actuator_cmd) = telemetry
```

**Priorities:** MissionStep > ReadSensors > FuseState > PlanAction > SafetyCheck > BuildTelemetry

Each child depends on the output of the previous. The parent controls the
chain of dependency. No child may execute before its inputs are available.

---

## Decomposition: ReadSensors — Include (Independent)

```
ReadSensors(raw_hazcam, raw_navcam, raw_imu) = (hazard_map, terrain_map, pose)

Include [independent — children share no inputs or outputs with each other]
 |-- ProcessHazCam(raw_hazcam) = hazard_map        [independent]
 |-- ProcessNavCam(raw_navcam) = terrain_map        [independent]
 '-- ProcessIMU(raw_imu) = pose                     [independent]
```

**Axiom 3 assignments:** Each child produces exactly one output. No child
writes to another child's output. The parent collects all outputs.

**Axiom 4 assignments:** Each child receives exactly one input from the
parent. No child reads another child's input.

**Axiom 6:** Because children are independent, execution order does not
affect the result. However, in a resource-constrained environment (single
CPU), the parent controls scheduling priority:
`ProcessHazCam > ProcessNavCam > ProcessIMU`

Hazard detection has highest priority — if the rover is about to drive off
a cliff, the hazard map must be ready before terrain or pose processing
completes. This mirrors Hamilton's GN&C priority ordering (Figure 8,
CSER 2007, p.10): Control > Guidance > Navigation.

---

## Decomposition: PlanAction — Or (Decision)

```
PlanAction(world_model, mission_cmd) = planned_cmd

Or [mission_cmd.phase — exactly one child executes]
 |-- [phase == "traverse"]  -> PlanTraverse(world_model, mission_cmd) = planned_cmd
 |-- [phase == "sample"]    -> PlanSample(world_model, mission_cmd) = planned_cmd
 '-- [phase == "safe_hold"] -> HoldPosition(world_model) = planned_cmd
```

**Or rules (Figure 2):**
- Inputs of all children are identical to parent inputs (including order).
- Outputs of all children are identical to parent outputs (including order).
- Parent uses `mission_cmd.phase` as partition condition to select exactly
  one child. The unselected children do not execute.

---

## Decomposition: SafetyCheck — Or (Decision)

```
SafetyCheck(world_model, planned_cmd) = actuator_cmd

Or [world_model.hazard_detected — exactly one child executes]
 |-- [hazard_detected == true]  -> EmergencyStop(world_model) = actuator_cmd
 '-- [hazard_detected == false] -> PassThrough(planned_cmd) = actuator_cmd
```

This is the critical safety gate. The planned command from the mission
planner is only forwarded to the actuators if no hazard is detected.
If a hazard is detected, `EmergencyStop` produces a halt command regardless
of what the planner wanted.

**Key Axiom 3 property:** `PlanAction` never writes to `actuator_cmd` directly.
It produces `planned_cmd` (a local). Only `SafetyCheck` produces
`actuator_cmd` (an output of the parent). This ensures the safety gate
cannot be bypassed — the planner has no access to the actuator output
variable.

---

## Axiom Compliance Summary

| Axiom | How this map satisfies it |
|-------|--------------------------|
| 1 — Invocation | MissionStep invokes only its immediate children. No child calls a sibling or grandchild. |
| 2 — Output Responsibility | Every child returns to the parent. No fire-and-forget. No endless loops (all functions are bounded). MissionStep ensures delivery of (actuator_cmd, telemetry). |
| 3 — Output Access Rights | Each output variable is assigned to exactly one child. `actuator_cmd` is produced only by SafetyCheck. `telemetry` is produced only by BuildTelemetry. No child writes to another child's output. |
| 4 — Input Access Rights | Each child receives only the inputs assigned by the parent. No child reads global state or another child's inputs. Inputs are for reference only — no child mutates them. |
| 5 — Domain Validation | Each sensor processor must reject invalid readings (corrupt data, out-of-range values). FuseState must reject inconsistent sensor data. SafetyCheck must reject malformed planned commands. |
| 6 — Ordering/Priority | The Join enforces sequential ordering via data dependency. The Include allows parallel execution with priority: HazCam > NavCam > IMU. SafetyCheck always executes after PlanAction — the safety gate is never bypassed. |
