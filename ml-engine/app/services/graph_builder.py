"""
ml-engine/app/services/graph_builder.py
Owner: Person 2 | Week: 1 (schema) -> Week 3 (full implementation)

Builds and maintains the service dependency graph using networkx (already in
requirements.txt). Source data: sample-data/sample_dependencies.csv and/or the
`services` / `service_dependencies` tables seeded in docker/postgres/init.sql.
- build_graph(): construct graph from DB or CSV topology
- update_graph(): add/remove nodes and edges as topology changes
Queried by api/graph_traversal.py and consumed by genai-agent for RCA.
"""
