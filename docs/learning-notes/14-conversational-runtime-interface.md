# Learning Note: Conversational Runtime Interface

Phase 1 introduced a controlled multi-step runtime, but the demo still exposed that runtime as a separate mode.

Phase 2 moves the system toward a better interaction model:

- one chat surface for the user
- multiple controlled execution paths underneath

## The Main Idea

The important architectural shift is:

- keep the runtime controlled
- make the interface conversational

That means the user does not need to decide whether they are making a normal QA request or starting a workflow.

Instead, the system evaluates each turn and routes it to the correct execution path.

## Why Not Let The Model Freely Pick Tools?

It would be tempting to let the model decide:

- which tool to call
- whether to retrieve
- whether to write an email

But that would collapse the design back into an open agent loop.

The better pattern for this repo is:

- chat is the interface
- routing is system-controlled
- workflow execution is typed and bounded

## Phase 2 Routing Model

For the legal QA app, the conversational runtime now uses:

- in-memory session state
- follow-up rewriting for contextual QA turns
- heuristic detection of email-oriented workflow instructions

Examples:

- `What does Article 12 say?`
  - routed to standard QA
- `What about the penalties for that?`
  - routed to standard QA with prior question context injected
- `Please draft an email summarizing this to legal-team@example.com`
  - routed to the controlled `answer_and_draft_email` workflow

## What This Achieves

This is a stronger system shape than either extreme:

- stronger than a plain request-response chat API
- safer than a free-form agent loop

It demonstrates a useful middle ground:

- conversational UX
- controlled runtime underneath
- auditable workflow execution when the turn becomes action-oriented

## Current Limits

Phase 2 is intentionally small:

- sessions are in-memory only
- routing is heuristic
- there is no clarification turn yet

That is acceptable for now because the goal is to prove the architecture, not to build a full conversation platform in one step.
