# Hamilton's Six Axioms of Control — Code Analysis Reference

> Derived from Margaret H. Hamilton's "Universal Systems Language for Preventative Systems Engineering" (CSER 2007) and the empirical study of the Apollo on-board flight software. These axioms define the formal relationships of control between a parent and its children in any system hierarchy.
>
> Primary source: `docs/verification/usl-for-preventative-systems-engineering.pdf`

---

## Foundational Concepts

### System Oriented Objects (SOOs)

> *"Every object is a system oriented object (SOO), itself defined in terms of other SOOs. A SOO inherently integrates all aspects (e.g., function, object and timing oriented) of a system; every system is an object, every object is a system."*
> — Hamilton & Hackler, CSER 2007, p.3

A SOO is the fundamental unit in 001AXES. The recursive composition property — reliable systems are defined in terms of reliable systems, only reliable systems are used as building blocks, and only reliable systems are used as mechanisms to integrate these building blocks — is what allows the axioms to guarantee correctness at every level of the hierarchy.

### FMaps and TMaps

All representations of a system are defined in terms of two complementary map types:

- **FMap (Functional Map):** Defines the dynamic (doing) world of action — functions, their inputs/outputs, and control flow. Captures functional and time (including priority) characteristics. The axioms of control govern parent-child relationships on an FMap.

- **TMap (Type Map):** Defines the static (being) world of objects — types, their spatial relationships, and containment. Captures structural characteristics (e.g., containment of one object by another).

> *"FMaps are used for defining functions and their relationships to other functions using the types of objects in the TMap(s). Each function on an FMap has one or more objects as its input and one or more objects as its output."*
> — Hamilton & Hackler, CSER 2007, p.7

FMaps and TMaps are inherently integrated: FMaps are defined in terms of TMaps, and TMaps are defined in terms of FMaps. Every type on a TMap owns a set of inherited primitive operations for its allowed FMap functional relationships.

### Maps and Decomposition

> *"With a map, everything you need to know (no more, no less) is available."*
> — Hamilton & Hackler, CSER 2007, p.7

A hierarchical definition is decomposed until the primitive objects have been reached. Resident at every node on an FMap is a function; resident on every node of a TMap is a type. The object at each node plays multiple roles — it can serve as a parent (in control of its children) or a child (being controlled by its parent). The decomposition stopping point can be determined and the bottom is reached when each function has been defined in terms of other functions on a defined type, one level from the bottom. The behavior of the top node is ultimately determined by the behavior of the collective set of bottom nodes.

---

## Axiom 1 — Control of Invocation

A parent controls the invocation of **only its immediate children**. The children collectively perform **no more and no less** than the parent's requirements. A parent cannot invoke itself, its own parent, its grandchildren, or siblings. No child should be extraneous — if removing a lower-level function leaves the parent's behavior unchanged, that function violates this axiom.

**What to look for:**

- Functions calling grandchildren directly (skipping levels of abstraction)
- Dead code or unreachable functions
- Functions whose removal wouldn't change parent behavior (extraneous functions proliferate test cases and complicate interfaces)
- Circular invocation (a child invoking its parent)
- A function invoking siblings — children of its own parent that it has no business calling

---

## Axiom 2 — Control of Output Responsibility (Codomain)

A parent is responsible for producing the correct output for every valid input. It may delegate work to children, but **it cannot delegate this responsibility**. The parent must ensure delivery of its output. A parent loses control when any of its children stop before completion, enter an endless loop, or fail to return required information.

**What to look for:**

- Children that stop before completion without the parent handling it (uncaught exceptions, early returns with no value)
- Children that can enter endless loops or deadlocks (blocking the parent from ever producing output)
- Children that fail to return required information to the parent (**severed return paths**, fire-and-forget calls where results are needed)
- Error swallowing — catching exceptions and continuing without producing the correct output
- Missing or incomplete return values from child functions

---

## Axiom 3 — Control of Output Access Rights

A parent controls **which output variables each immediate child may alter**. Each output variable of the parent must appear as an output of at least one child. Outputs are traceable instance by instance. The parent assigns to its children the right to alter specific output variables — no more, no less.

**What to look for:**

- Children writing to variables/state outside their assigned scope (global state mutation, writing to shared mutable state without parent mediation)
- Parent outputs that no child produces (dead output paths)
- Untraceable output modifications (side effects hidden in nested calls)
- Multiple children writing to the same output without parent-controlled coordination
- Children modifying state that belongs to other children or other parents

---

## Axiom 4 — Control of Input Access Rights

A parent controls **which input variables each immediate child may read**. Children receive inputs **for reference only** — they cannot alter the parent's inputs. Each input of the parent must be consumed by at least one child. The parent does not have the ability to alter its own domain elements either.

**What to look for:**

- Children mutating input parameters or input state (pass-by-reference mutation, modifying shared input objects)
- Parent inputs that no child ever reads (unused parameters)
- Children accessing inputs not granted by the parent (reaching into global state, environment variables, or closures for data that should flow through the interface)
- A parent modifying its own inputs before delegating to children

---

## Axiom 5 — Control of Error Detection and Rejection (Domain Validation)

A parent **must detect and reject** any input that is not in its valid domain. If an invalid input is received, the parent must ensure its rejection — not silently pass it to children, not log a warning and continue, not downgrade to a default.

> *"Axiom 5 states that a given parent controls the rejection of invalid elements of its own, and only its own, input set (domain). It requires that the parent must ensure the rejection of inputs received that are not in the domain of the parent. A parent, in performing its corresponding function, is responsible for determining if such an element has been received; if so, it must ensure its rejection."*
> — Hamilton & Hackler, CSER 2007, p.5

**Key clarification:** Domain validation is the responsibility of **each parent at its own level**, not just at system boundaries. However, a parent validates only **its own** domain — if a parent's child has already validated and transformed data into the child's output (which becomes the next function's input), the next function's domain is that validated output. This means: once the loader (parent) has validated Lua content and compiled it to Go structs, downstream engine functions receive those structs as their domain — the loader's Axiom 5 enforcement has already established their validity. Domain validation at internal boundaries is necessary only when the domain of the receiving function is narrower than or different from what the producing function guarantees.

**What to look for:**

- Missing input validation at function/module boundaries
- Errors being swallowed or downgraded (caught exceptions with no meaningful handling)
- Invalid inputs propagating silently to children
- Warnings logged where errors should be raised (the warning-without-recovery anti-pattern)
- Missing reject/error paths for edge cases
- Defensive programming that masks invalid state instead of rejecting it

---

## Axiom 6 — Control of Ordering and Priority

A parent controls the **execution order and priority** of its immediate children and their descendants. Priority is totally ordered: a parent's priority is always higher than its children's. Among siblings, ordering is deterministic and controlled by the parent. A process cannot interrupt itself or its parent. Dependent functions must exist at the same level.

**What to look for:**

- Race conditions from uncontrolled concurrent access
- Missing priority/ordering in task scheduling
- Children that can block or starve their parent
- Non-deterministic execution order where determinism is required
- Missing synchronization between dependent siblings
- Priority inversion (a child effectively taking priority over its parent)
- Dependent functions scattered across different levels of the hierarchy

---

## Cross-Axiom Derived Rules

These rules emerge from the interaction of multiple axioms. Hamilton calls them "derived theorems" — they are logical consequences of the axioms, not additional assumptions.

> *"Other implications (derived theorems) of the axioms are: every object has a unique parent, is under control and has a unique priority; communication of children is controlled by the parent, and dependent functions exist at the same level; the priority of an object is always higher than its dependents and totally ordered with respect to other objects at its own level."*
> — Hamilton & Hackler, CSER 2007, p.6

### Output/Input Set Separation (Axioms 3 + 4)
A function's output variables **cannot** also be its input variables. If `f(y, x) = y` exists, access to `y` is uncontrolled by the parent at the next higher level. Outputs of one function can be inputs of another function only if both are at the same level.

> *"If f1(x) = y and f2(y) = g, both functions exist at the same level."*
> — Hamilton & Hackler, CSER 2007, p.5

### Completeness of Return Paths (Axioms 1 + 2)
Every invocation path must return control and data to the parent. **Severed return paths are the most critical violation pattern.** If a child is invoked and cannot return its result to the parent, the parent has lost control of its own output responsibility.

### Single Reference / Single Assignment (Axioms 3 + 4 + 6)
Each variable's relationships are predetermined instance by instance — no aliasing conflicts, no concurrent uncontrolled writes. SOOs can be defined independent of execution order because of this property.

> *"The relationships of each variable are predetermined, instance by instance thus eliminating conflicts; each system has the property of single reference/single assignment. SOOs can therefore be defined independent of execution order."*
> — Hamilton & Hackler, CSER 2007, p.6

### Nodal Family Independence (Axioms 1 + 4)
A parent and its children do not know about (are independent of) their invokers or users. This means a function should not behave differently based on who called it — it should depend only on its declared inputs.

> *"The nodal family (a parent and its children) does not know about (is independent of) its invokers or users."*
> — Hamilton & Hackler, CSER 2007, p.6

### Unique Parent and Unique Priority (Axioms 1 + 6)
Every object has a unique parent, is under control, and has a unique priority. Communication of children is controlled by the parent. Dependent functions exist at the same level.

### Concurrent Pattern Detection (Axioms 3 + 4 + 6)
Because of the single reference/single assignment property, concurrent patterns (independencies and dependencies) can be readily detected — manually or automatically — and used to determine where parallel and distributed processing is most beneficial.

---

## Primitive Control Structures

> *"Every system can ultimately be defined in terms of three primitive control structures, each of which is derived from the six axioms."*
> — Hamilton & Hackler, CSER 2007

A structure relates members of a nodal family (a parent and its children) according to a set of rules derived from the axioms of control. A primitive structure provides a relationship of the most primitive form of control between objects on a map. All maps are defined ultimately in terms of three primitive control structures, and therefore abide by the formal rules associated with each structure.

These three primitives are **complete** (any system can be expressed in terms of them) and **closed** (composing them yields only structures that satisfy all six axioms). Non-primitive structures can be derived from them, but every such derivation is ultimately reducible to these three.

### The Böhm-Jacopini Connection

Hamilton's three primitive control structures correspond to the three constructs that Böhm and Jacopini (1966) proved sufficient to express any computable function. Every programmer already uses these structures daily — Hamilton's contribution is formalizing the *control rules* that make each structure safe.

| Hamilton Primitive | Böhm-Jacopini Construct | What programmers already write | Hamilton's added discipline |
|--------------------|------------------------|-------------------------------|----------------------------|
| **Join** | Sequence | `x=a(); y=b(x); z=c(y);` | Enforced data dependency — each step's output is the next step's input, controlled by the parent |
| **Include** | Concurrence / Parallel | Independent goroutines, ROS nodes, parallel pipelines | Enforced independence — children share no inputs/outputs with each other, only with the parent |
| **Or** | Selection / Branching | `if/else`, `switch/case`, pattern matching | Enforced mutual exclusion — exactly one child executes, selected by a parent-controlled condition |

The insight: you already write sequences, branches, and concurrent processes. Hamilton's axioms formalize the rules that make them *safe*. The question at each decomposition is not "what construct do I use?" — you already know that. The question is: **"are these children dependent, independent, or mutually exclusive?"** If you can answer that, the axioms are satisfied by construction.

### Join — Dependent Relationship

A parent controls its children to have a **dependent** relationship. The output of one child becomes the input of the next. Children must execute in the order dictated by their data dependencies — child B cannot begin until child A has produced the output that B requires.

> **Example:** Sending an email. Each child depends on the output of the previous — the parent controls this chain of dependency. You cannot compose a message without first knowing the address, and you cannot deliver without first composing the message.
>
> ```
> Dependent -- Composition:
> Parent(inputs) → outputs
>  ├── Left(inputs) → locals     [child 1]
>  └── Right(locals) → outputs   [child 2, depends on child 1]
> inputs, locals, and outputs are ordered sets of variables. Child 1 produces locals from inputs, and child 2 produces outputs from locals. The parent controls the order of execution because of the data dependency. Priorities: Parent > Left > Right
> ```

### Include — Independent Relationship

A parent controls its children to have an **independent** relationship. Children do not depend on each other's outputs. Each child receives its inputs directly from the parent and produces its outputs independently. Because they are independent, the parent controls whether they execute concurrently or in any order — the result is the same.

> **Example:** Reading from sensors. Each child independently reads one measurement in the specified unit and returns the value. No child depends on another's output. Because they are independent, execution order does not matter.
>
> ```
> Independent -- Class partition:
> Parent(inputs1, inputs2) → outputs1, outputs2
>  ├── Left(inputs1)    → outputs1  [independent]
>  └── Right(inputs2)   → outputs2  [independent]
> Parent sends all its inputs to its children. Children sends all their outputs to parent.
> Order of inputs and outputs are maintained, but children do NOT share inputs or outputs.
> Left inputs receives left most inputs. Right receives the rest. Left produces left most outputs. Right produces the rest.
> ```

### Or — Decision Making Relationship

A parent controls its children to have a **decision making** relationship. The parent evaluates a condition on its input and selects **exactly one** child to execute. The children are mutually exclusive — only the selected child performs its mapping. The unselected children do not execute.

> **Example:** Dispatching an emergency call. The parent evaluates the type of emergency and dispatches exactly one service. Only one child executes per invocation — the others do not run.
>
> ```
> Decision Making -- Set Partition:
> Parent (inputs) → outputs
>  ├── [property == true] → Left(inputs) → outputs
>  └── [property == false] → Right(inputs) → outputs
> Inputs of both children are identical to parent (included order).
> Outputs of both children are identical to parent (including order).
> Input of partition are identical to parent. (including order).
> Parent uses partition condition to select exactly one child to execute.
> ```

### Composition

Any system, no matter how complex, is defined by composing these three primitives. A Join may contain an Or at one of its steps. An Or branch may itself be a Join. An Include's independent children may each internally be defined as Joins or Ors. Because the primitives satisfy the six axioms, and because composition preserves axiom satisfaction, the resulting system is correct by construction — the entire class of interface errors is eliminated at the definition phase.

> **Source:** Hamilton, M. and Hackler, W.R., "Universal Systems Language for Preventative Systems Engineering," CSER 2007, Stevens Institute of Technology. Primitive structures are defined in Figures 1–3 and the "Universal Primitive Structures" section of the paper. The structural rules for FMap application are in Figure 2.

---
## Origin

These axioms were derived from the empirical study of the Apollo on-board flight software, where interface errors (data flow, priority, and timing errors) accounted for approximately 75% of all errors found. The axioms define a formal foundation such that **the entire class of interface errors is eliminated by construction** — the "Development Before the Fact" paradigm. Hamilton's key insight: the root problem with traditional approaches is that they support "fixing wrong things up" rather than "doing things in the right way in the first place."

> *"Correctness is accomplished by how a system is defined, by 'built-in' language properties."*
> — Margaret H. Hamilton
