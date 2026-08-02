"""
ml-engine/app/api/graph_traversal.py
Owner: Person 2 | Week: 3

Exposes dependency graph traversal as an API endpoint for the GenAI agent layer.
- GET /api/graph/traverse?service={name} -> returns propagation path / affected
  services, using services/graph_builder.py's graph
- Implements graph-based dependency resolution: given a failing service, trace
  upstream/downstream impact
- Contract defined in shared/api-contracts.md
"""
