# CLAUDE.md — Mars Rover DBTF Demo

## What This Is

A demonstration project showing Development Before the Fact (DBTF)
applied to a Mars rover autonomy controller. The purpose is to show
that AI can assist in defining, verifying, and implementing systems
using Hamilton's six axioms of control — catching interface errors
at the definition phase, not during testing.

This is a control-logic-only project. No physics simulation, no
graphics, no real sensors. The focus is entirely on the formal
structure of the controller and its axiom compliance.

## Development Approach

### Definition Before Implementation

1. Define FMaps from requirements (`docs/fmaps/`)
2. Verify axiom compliance on the maps before writing code
3. Implement code from verified maps (`src/`)
4. Verify code against maps — detect any structural drift

### Hamilton's Six Axioms

The reference for the six axioms and primitive control structures:
- `docs/hamilton-six-axioms-reference.md` — working reference for code analysis
- `docs/usl-for-preventative-systems-engineering.pdf` — primary source (Hamilton & Hackler, CSER 2007)

### Verification Methods

FMaps are verified using scan types defined in the reference:
- **Single File Scan — Violation Detection (ATF):** Scan code against each axiom.
- **Single File Scan — Structural Classification (BTF):** Classify each function's decomposition as Join, Include, or Or.
- **Cross-Module Trace:** Trace call paths and verify Axiom 2 (output responsibility) at each boundary.
- **FMap Diff:** Compare implemented code structure against the defined FMap. Flag any structural drift.

## Language

Python. Chosen because it is the standard in robotics (ROS, MicroPython)
and because its permissiveness (mutable references, global state, no
compiler type checks) makes DBTF's structural discipline more valuable —
the axioms do the work the language won't.

## Project Structure

```
docs/
  fmaps/          -- FMap definitions (BEFORE code)
  verification/   -- Axiom scans, violation reports, FMap diffs
src/              -- Implementation
tests/            -- Test scenarios
```

## Conventions

- FMaps are defined before code. Code follows maps, not the other way around.
- Every function must be traceable to a node on an FMap.
- No global mutable state. All data flows through function parameters and return values.
- Every Or must have exhaustive branches. No implicit default that silently drops input.
- Every function validates its own domain (Axiom 5) — invalid inputs are rejected, not silently passed to children.
