# CLAUDE.md — Mars Rover DBTF Demo

## What This Is

A demonstration project showing Development Before the Fact (DBTF)
applied to a Mars rover autonomy controller. The purpose is to show
that AI-assisted axiomatic verification can catch interface errors
as static analysis — before any code is executed, before tests run,
before a push.

This is a control-logic-only project. No physics simulation, no
graphics, no real sensors. The focus is entirely on the formal
structure of the controller and its axiom compliance.

## How DBTF Fits Into Normal Development

DBTF is not a waterfall methodology. It enters the workflow as
**static analysis** — the same way a linter does. The developer
writes code normally. Before it runs, the axiomatic verification
reads the code and checks the control structure against Hamilton's
six axioms.

### Pipeline Position

```
lint → axiomatic verification → test → build
```

- **Lint** catches syntax and style.
- **Axiomatic verification** catches structural errors: wrong data flow,
  uncontrolled mutation, severed return paths, missing domain rejection.
  These are the interface errors that account for 75-90% of bugs found
  during traditional testing (Hamilton & Hackler, CSER 2007, p.6-7).
- **Tests** catch behavioral errors — does the planner actually produce
  the right waypoint? Tests should focus on behavior, not on interface
  errors that the structure already prevents.

### Local Verification

Axiomatic verification should run locally before `git push`, not only
in CI. The developer catches violations at their desk, not in a pipeline
30 minutes later.

### When Verification Applies

The verification becomes useful the moment a function has been
**decomposed** — when the developer has written the body and decided
which children to call, in what order, with what arguments. That's
when the control hierarchy exists and the axioms can be checked.

## Hamilton's Six Axioms

The reference for the six axioms and primitive control structures:
- `docs/hamilton-six-axioms-reference.md` — working reference for code analysis
- `docs/usl-for-preventative-systems-engineering.pdf` — primary source (Hamilton & Hackler, CSER 2007)

## Verification Methods

- **Single File Scan — Violation Detection (ATF):** Scan code against each axiom. Report PASS, WARN, or FAIL with line numbers.
- **Single File Scan — Structural Classification (BTF):** Classify each function's decomposition as Join, Include, or Or. Flag mixed decompositions.
- **Cross-Module Trace:** Trace call paths and verify Axiom 2 (output responsibility) at each boundary.

## Language

Python. Chosen because it is the standard in robotics (ROS, MicroPython)
and because its permissiveness (mutable references, global state, no
compiler type checks) makes DBTF's structural discipline more valuable —
the axioms do the work the language won't.

## Project Structure

```
docs/
  fmaps/          -- FMap analyses (derived from code, not the other way around)
  verification/   -- Axiom scan reports
src/              -- Implementation
tests/            -- Behavioral tests
```

## Conventions

- No global mutable state. All data flows through function parameters and return values.
- Every Or must have exhaustive branches. No implicit default that silently drops input.
- Every function validates its own domain (Axiom 5) — invalid inputs are rejected, not silently passed to children.
