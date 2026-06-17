# ADR 012: Multi-Agent Orchestration (Supervisor-Worker)

## Status

Proposed

## Context

Phase 1 (ADR 010) introduced a controlled agent runtime under `src/genai_gateway/runtime/agent/`: a typed planner compiles a task into a bounded sequential plan, a `ToolExecutor` dispatches plan steps to typed capabilities, and the `AgentOrchestrator` runs per-step checkpoints.

The current runtime has a single executor running a flat list of capabilities. There is no notion of specialized agents that own a sub-task and can be composed, reviewed, or reused independently. The next architectural step is multi-agent collaboration — specialized agents that delegate sub-tasks and share context — without losing the design values stated in ADR 010: controllability, auditability, latency predictability, and step-level evaluation.

This ADR covers orchestration only. The memory tiers that make multi-agent runs personalized and self-improving are specified in ADR 013, which builds on the shared context introduced here.

## Decision

Introduce a **supervisor-worker** topology, not peer-to-peer messaging.

- Add `SpecializedAgent` (ABC) under `src/genai_gateway/runtime/agent/agents/base.py`: a bounded role that owns a capability subset and exposes `run(subtask, shared_context) -> SubTaskResult`.
- Add initial agents that **wrap existing capabilities** (no rewrite of `src/genai_gateway/tools/`):
  - `ResearchAgent` — `retrieve_context` + grounded synthesis (`answer_question`)
  - `DraftingAgent` — `draft_email`, and future document drafting
  - `ReviewAgent` — an explicit critic that validates a peer agent's output (groundedness, scope, completeness) for cross-agent self-correction
- Add `SupervisorOrchestrator` (`src/genai_gateway/runtime/agent/supervisor.py`) extending the Phase 1 orchestrator: it compiles an **agent-level delegation plan** and runs agents under the same checkpoint discipline, now applied at the inter-agent boundary.
- Add a typed shared context (`src/genai_gateway/runtime/agent/shared_context.py`) that evolves `AgentExecutionState` into a **typed blackboard**: agents read/write named, typed slots instead of passing raw message history.
- Extend `schemas.py` with `AgentRole`, `SubTaskRequest`, `SubTaskResult`, and `DelegationPlan`, mirroring the existing `PlanStep` / `StepResult` shapes.

Delegation is **rule-based first**, consistent with the Phase 1 planner.

Phase 3a explicitly does not support:

- LLM-driven dynamic delegation or dynamic agent/tool discovery
- peer-to-peer agent messaging
- dynamic agent spawning

## Execution Model

```text
SupervisorOrchestrator
  ├─ delegate → ResearchAgent   ─┐
  │     checkpoint (evidence, groundedness)
  ├─ delegate → DraftingAgent    │ typed SubTaskRequest / SubTaskResult
  │     checkpoint (output valid) │ over a typed shared blackboard
  └─ delegate → ReviewAgent      ─┘
        checkpoint (critic: allow / revise / abort)
```

Each delegation is an explicit, logged `SubTaskRequest`; each agent returns a typed `SubTaskResult`; the supervisor checkpoints at the boundary before the next delegation, reusing `runtime/guardrails.py` and the evaluation scorers already used by the Phase 1 orchestrator.

## Why This Design

- **Reuses everything that already works**: capabilities, checkpoints, guardrails, model routing, request logging.
- **Supervisor-worker over free-form swarm**: matches the production failure modes the repo already rejects (context explosion, non-determinism, unauditable loops) and keeps latency bounded.
- **Typed blackboard over message passing**: bounds context growth and preserves auditability.
- **ReviewAgent as a first-class critic**: makes cross-agent self-correction an explicit, testable step rather than an emergent behavior.

## Evaluation (extends ADR 003)

- delegation correctness: did the supervisor route sub-tasks to the right agents
- cross-agent groundedness preservation: does `ReviewAgent` catch ungrounded peer output
- latency budget per added agent hop
- abort/revise rates at inter-agent checkpoints

## Consequences

Positive:

- specialized, independently testable agents with explicit cross-agent review
- typed boundaries between supervision, delegation, and execution
- stronger enterprise narrative than an unconstrained agent loop
- shared blackboard provides the context surface that ADR 013 memory plugs into

Tradeoffs:

- more moving parts: supervisor, agents, blackboard
- extra latency from agent hops (mitigated by bounded delegation; parallel sub-tasks deferred)
- rule-based delegation is less flexible than learned routing (intentional for this phase)

## Follow-up

- ADR 013: persistent memory tiers that condition and update supervised runs
- later: parallel independent sub-tasks, LLM-driven delegation, exposing agent tools over MCP (separate track)

## Implementation In This Repo

New modules (proposed):

- `src/genai_gateway/runtime/agent/agents/` — `base.py`, `research_agent.py`, `drafting_agent.py`, `review_agent.py`
- `src/genai_gateway/runtime/agent/supervisor.py`
- `src/genai_gateway/runtime/agent/shared_context.py`

Touched / extended:

- `src/genai_gateway/runtime/agent/schemas.py` — agent / delegation schemas
- `src/genai_gateway/runtime/service.py` — add `run_supervised_task`
- `src/genai_gateway/evaluation/` — agent-level eval signals
