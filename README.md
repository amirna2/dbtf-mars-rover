# DBTF Mars Rover

A Mars rover autonomy controller demonstrating **Development Before the Fact (DBTF)** with AI-assisted axiomatic verification.

DBTF is Margaret Hamilton's formal methodology for eliminating interface errors by construction. Hamilton developed it from the empirical study of the Apollo on-board flight software, where interface errors (data flow, priority, and timing errors) accounted for ~75-90% of all errors found during testing. The methodology is based on six axioms of control that, when satisfied, guarantee the absence of this entire class of errors.

This project shows that AI can perform axiomatic verification as **static analysis** — reading implemented code and checking its control structure against Hamilton's six axioms before any tests run.

## What This Demonstrates

1. **A developer writes a rover controller in Python** — sensor fusion, path planning, safety gate. Normal code, no special framework.

2. **AI performs axiomatic verification as static analysis** — classifies each function's decomposition (Join, Include, or Or), maps input/output variable assignments, and checks all six axioms. This runs before tests, like a linter.

3. **Structural errors are caught at definition, not during testing** — the verification catches issues that linters, type checkers, and unit tests miss: uncontrolled state mutation, severed return paths, missing domain validation, priority inversions.

4. **Tests focus on behavior, not interface correctness** — because the structure prevents interface errors, tests only need to verify that the rover actually navigates correctly, not that function A can't accidentally mutate function B's state.

## Pipeline Position

```
lint → axiomatic verification → test → build
```

The axiomatic verification step sits between linting and testing. It should run locally before `git push`, not only in CI.

## Project Structure

```
src/
  types.py          -- Immutable data types (frozen dataclasses)
  controller.py     -- Rover controller (sensor fusion, planning, safety)
docs/
  fmaps/            -- FMap analyses (control hierarchy maps)
  verification/     -- Axiomatic scan reports
  hamilton-six-axioms-reference.md
  usl-for-preventative-systems-engineering.pdf  -- Hamilton's original paper (CSER 2007)
tests/              -- Behavioral tests
```

## The Controller

The rover receives sensor data and a mission command, and produces an actuator command and telemetry:

```
step(sensors, mission_cmd) = (actuator_cmd, telemetry)

Join [dependent pipeline]
 |-- read_sensors(sensors) = (hazard_map, terrain_map, pose)
 |     Include [independent]
 |      |-- process_hazcam(hazcam) = hazard_map
 |      |-- process_navcam(navcam) = terrain_map
 |      '-- process_imu(imu) = pose
 |-- fuse_state(hazard_map, terrain_map, pose) = world_model
 |-- plan_action(world_model, mission_cmd) = planned_cmd
 |     Or [mission phase]
 |      |-- [traverse]  -> plan_traverse
 |      |-- [sample]    -> plan_sample
 |      '-- [safe_hold] -> hold_position
 |-- safety_check(world_model, planned_cmd) = actuator_cmd
 |     Or [hazard detected?]
 |      |-- [true]  -> emergency_stop
 |      '-- [false] -> pass_through
 '-- build_telemetry(world_model, actuator_cmd, mission_cmd) = telemetry
```

Key structural property: `plan_action` produces `planned_cmd` (a local), not `actuator_cmd` (the output). Only `safety_check` produces `actuator_cmd`. The safety gate cannot be bypassed — this is enforced by the Join's data dependency, not by a runtime check.

## Hamilton's Six Axioms

| Axiom | What It Controls |
|-------|-----------------|
| 1 — Invocation | A parent invokes only its immediate children. No skipping levels, no circular calls. |
| 2 — Output Responsibility | A parent must ensure delivery of its output. Children cannot sever the return path. |
| 3 — Output Access Rights | A parent controls which outputs each child may produce. No uncontrolled writes. |
| 4 — Input Access Rights | A parent controls which inputs each child may read. Inputs are for reference only. |
| 5 — Error Detection | A parent must reject invalid inputs. No silent pass-through, no warning-and-continue. |
| 6 — Ordering and Priority | A parent controls execution order and priority. Deterministic, no priority inversion. |

## References

- Hamilton, M. and Hackler, W.R., "Universal Systems Language for Preventative Systems Engineering," CSER 2007, Stevens Institute of Technology. ([included in docs/](docs/usl-for-preventative-systems-engineering.pdf))
- Hamilton, M., "Inside Development Before the Fact," Electronic Design, April 1994.
