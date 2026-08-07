"""
genai-agent/app/main.py
Owner: Person 1

FastAPI application entrypoint for the GenAI Agent service.
- Initializes the FastAPI app
- Registers routers: /diagnose (RCA pipeline) and /route (confidence routing, Week 4)
- Wires up the LangGraph StateGraph from app/graph/state_graph.py on startup
- Calls ml-engine's api/graph_traversal.py endpoint for dependency graph queries
  (see shared/api-contracts.md for the contract)
"""
