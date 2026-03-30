# Axiomatic Verification — src/controller.py

**Date:** 2026-03-30
**File:** `src/controller.py` (283 lines)
**Types:** `src/types.py` (139 lines)
**Reference:** `docs/hamilton-six-axioms-reference.md`

---

## Step 1: Structural Classification

| Function | Structure | Children | Classification |
|----------|-----------|----------|----------------|
| `step` | Join | `read_sensors` → `fuse_state` → `plan_action` → `safety_check` → `build_telemetry` | PASS — pure dependent chain, each child's output feeds the next |
| `read_sensors` | Include | `process_hazcam`, `process_navcam`, `process_imu` | PASS — children share no inputs or outputs with each other |
| `process_hazcam` | Leaf | — | N/A |
| `process_navcam` | Leaf | — | N/A |
| `process_imu` | Leaf | — | N/A |
| `fuse_state` | Leaf | — | N/A |
| `plan_action` | Or | `plan_traverse`, `plan_sample`, `hold_position` | WARN — see Finding 1 |
| `plan_traverse` | Or (internal) | turn / drive / halt branches | PASS — exhaustive with explicit returns |
| `plan_sample` | Leaf | — | N/A |
| `hold_position` | Leaf | — | N/A |
| `safety_check` | Or | `emergency_stop`, `pass_through` | PASS — exhaustive, two branches |
| `emergency_stop` | Leaf | — | N/A |
| `pass_through` | Leaf | — | N/A |
| `build_telemetry` | Leaf | — | N/A |

No function mixes dependent and independent children in the same decomposition.

---

## Step 2: Axiom Scan

### Axiom 1 — Control of Invocation: **PASS**

Invocation hierarchy is clean:
- `step` calls only its 5 immediate children (lines 52-57)
- `read_sensors` calls only its 3 immediate children (lines 73-75)
- `plan_action` calls only its 3 immediate children (lines 174, 176, 178)
- `safety_check` calls only its 2 immediate children (lines 250, 252)
- No child calls a sibling, parent, or grandchild
- No circular invocations
- No dead code or unreachable functions

All functions are free functions (no class, no `self`). No child can reach into a parent's scope.

### Axiom 2 — Control of Output Responsibility: **PASS**

Every child returns to its parent on every code path:
- All leaf functions have a single `return` statement
- `plan_action` returns on all three branches plus a final `raise` for exhaustiveness (line 181)
- `plan_traverse` returns on all three branches: turn (line 206), halt (line 214), drive (line 216)
- `safety_check` returns on both branches via `if/else` (lines 250, 252)
- No fire-and-forget calls. No goroutines/threads. No endless loops.
- Sensor processors and planners raise exceptions on invalid input — these propagate to the parent (`step`), which does not catch them. The parent's caller is responsible for handling sensor/planner failures. This is correct: `step` cannot produce valid `(actuator_cmd, telemetry)` from invalid sensor data, so it should not try.

### Axiom 3 — Control of Output Access Rights: **PASS**

Output variable assignments for `step`:

| Child | Assigned outputs | Actual outputs | Violation? |
|-------|-----------------|----------------|------------|
| `read_sensors` | `hazard_map`, `terrain_map`, `pose` | `hazard_map`, `terrain_map`, `pose` | No |
| `fuse_state` | `world_model` | `world_model` | No |
| `plan_action` | `planned_cmd` | `planned_cmd` | No |
| `safety_check` | `actuator_cmd` | `actuator_cmd` | No |
| `build_telemetry` | `telemetry` | `telemetry` | No |

- No child writes to a variable assigned to another child
- No global state mutation anywhere
- All types are `frozen=True` dataclasses — mutation is structurally impossible
- `plan_action` produces `planned_cmd` (a local), NOT `actuator_cmd` (the parent output). Only `safety_check` produces `actuator_cmd`. The safety gate cannot be bypassed.

Output variable assignments for `read_sensors` (Include):

| Child | Assigned outputs | Shares with siblings? | Violation? |
|-------|-----------------|----------------------|------------|
| `process_hazcam` | `hazard_map` | No | No |
| `process_navcam` | `terrain_map` | No | No |
| `process_imu` | `pose` | No | No |

Children produce disjoint outputs. Include rule satisfied.

### Axiom 4 — Control of Input Access Rights: **PASS**

Input variable assignments for `step`:

| Child | Receives from parent | Accesses anything else? | Violation? |
|-------|---------------------|------------------------|------------|
| `read_sensors` | `sensors` | No | No |
| `fuse_state` | `hazard_map`, `terrain_map`, `pose` (locals from child 1) | No | No |
| `plan_action` | `world_model` (local from child 2), `mission_cmd` (parent input) | No | No |
| `safety_check` | `world_model` (local from child 2), `planned_cmd` (local from child 3) | No | No |
| `build_telemetry` | `world_model`, `actuator_cmd`, `mission_cmd` | No | No |

- No child accesses global state, environment variables, or closures
- All inputs flow through function parameters
- All types are `frozen=True` — children cannot mutate inputs
- Every parent input is consumed: `sensors` by `read_sensors`, `mission_cmd` by `plan_action` and `build_telemetry`

Input assignments for `read_sensors` (Include):

| Child | Receives | Shares inputs with siblings? | Violation? |
|-------|----------|------------------------------|------------|
| `process_hazcam` | `sensors.hazcam` | No | No |
| `process_navcam` | `sensors.navcam` | No | No |
| `process_imu` | `sensors.imu` | No | No |

Children receive disjoint inputs. Include rule satisfied.

### Axiom 5 — Control of Error Detection and Rejection: **WARN** (2 findings)

#### Finding 1 — `plan_action`: Or partition on enum but isinstance check is redundant

| | |
|---|---|
| **Severity** | LOW |
| **Location** | `controller.py:170-171` |
| **Pattern** | Unnecessary validation |

```python
if not isinstance(mission_cmd.phase, MissionPhase):
    raise PlannerError(f"Unknown mission phase: {mission_cmd.phase}")
```

`MissionCommand.phase` is typed as `MissionPhase` (an Enum). The `isinstance` check on line 170 guards against a caller passing a non-enum value. In Python this is possible (no runtime type enforcement), so the check is defensible. However, the `raise PlannerError` on line 181 is unreachable — if `phase` is a valid `MissionPhase`, one of the three `if/elif` branches will match. The final raise is dead code.

**Assessment:** The dead raise on line 181 is not harmful — it's a safety net for future enum additions. But strictly, it's an extraneous code path (Axiom 1: no child should be extraneous). Acceptable as defensive practice.

#### Finding 2 — `step` does not validate its own domain

| | |
|---|---|
| **Severity** | MEDIUM |
| **Location** | `controller.py:47-57` |
| **Pattern** | Missing domain validation at function boundary |

`step()` is the top-level entry point — the system boundary. It receives `sensors` and `mission_cmd` from an external caller. It performs no validation of its own inputs before passing them to children:

- Does not check if `sensors` is None
- Does not check if `mission_cmd` is None
- Does not check if `sensors.hazcam`, `sensors.navcam`, `sensors.imu` are present

The children (`process_hazcam`, `process_navcam`, `process_imu`) validate their own inputs (pixel data, timestamps), and `plan_action` validates the mission phase. But `step` itself — as the parent at the system boundary — does not validate its domain.

Per Axiom 5: *"A parent, in performing its corresponding function, is responsible for determining if such an element has been received; if so, it must ensure its rejection."*

**Recommendation:** Add domain validation at the top of `step()`:
```python
if sensors is None:
    raise SensorError("sensors input is None")
if mission_cmd is None:
    raise PlannerError("mission_cmd input is None")
```

This is a system boundary. The children validate their specific domains (pixel data, timestamps, mission phase), but the parent should reject obviously invalid inputs before delegating.

### Axiom 6 — Control of Ordering and Priority: **PASS**

- `step` is a Join — sequential execution enforced by data dependencies. Each child cannot execute before its inputs are available from the previous child.
- `read_sensors` is an Include — children are independent. Currently executed sequentially (lines 73-75), which is valid (Include allows any order). If parallelized in the future, no data races would occur because inputs are disjoint and outputs are disjoint.
- `plan_action` and `safety_check` are Or — exactly one branch executes, controlled by parent condition.
- No threads, no async, no shared mutable state. Ordering is fully deterministic.
- `safety_check` executes AFTER `plan_action` in the Join — the safety gate always has the final say. This ordering is critical and correctly enforced by data dependency (`safety_check` requires `planned_cmd` from `plan_action`).

---

## Step 3: Cross-Axiom Derived Rules

### Output/Input Set Separation (Axioms 3 + 4): **PASS**
No function's output variables are also its input variables. All types are frozen — even if a variable name is reused, the value is a new immutable object.

### Completeness of Return Paths (Axioms 1 + 2): **PASS**
Every invocation path returns. No severed return paths. Exceptions propagate upward — they are not swallowed.

### Single Reference / Single Assignment (Axioms 3 + 4 + 6): **PASS**
Each local variable is assigned exactly once. No variable is written by multiple children. Frozen dataclasses prevent aliasing mutations.

### Nodal Family Independence (Axioms 1 + 4): **PASS**
No function behaves differently based on who called it. All behavior depends solely on declared inputs. No global state, no closures over mutable state.

---

## Summary

| Axiom | Verdict | Findings |
|-------|---------|----------|
| 1 — Control of Invocation | **PASS** | 0 |
| 2 — Control of Output Responsibility | **PASS** | 0 |
| 3 — Control of Output Access Rights | **PASS** | 0 |
| 4 — Control of Input Access Rights | **PASS** | 0 |
| 5 — Control of Error Detection/Rejection | **WARN** | 1 LOW, 1 MEDIUM |
| 6 — Control of Ordering and Priority | **PASS** | 0 |

**Overall: The controller's control structure is axiom-compliant.** The frozen dataclass pattern in Python provides structural enforcement of Axioms 3 and 4 that would otherwise depend on developer discipline. The one actionable finding is the missing domain validation in `step()` at the system boundary.
