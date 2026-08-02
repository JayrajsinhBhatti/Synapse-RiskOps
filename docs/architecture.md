# Architecture

Owner: Joint | Week 1 (initial state machine) -> Week 6 (final documentation)

This doc should cover:
- End-to-end pipeline diagram: metrics -> preprocessing -> risk prediction ->
  branch (healthy / incident) -> RCA -> guidance -> automation -> verify recovery
  -> healthy again / escalate
- State machine diagram of the pipeline (Person 1's Week 1 deliverable — see
  docs/state_machine_diagram.png)
- Service-by-service architecture: ml-engine, genai-agent, backend, frontend,
  automation, and how they communicate (matches shared/api-contracts.md)
- Design decisions, limitations, and future improvements (final report content)

See also docs/PERSON2_DOCS_README.md for Person 2's existing service notes.
