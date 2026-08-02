"""
genai-agent/app/graph/state_graph.py
Owner: Person 1 | Week: 3

Defines the LangGraph StateGraph wiring together the three agents:
LogAnalyzer -> RootCauseIdentifier -> GuidanceGenerator
- Defines the shared agent state object passed between nodes
- Defines edges/transitions between agent nodes
- Compiles the graph into a runnable pipeline invoked by /diagnose in main.py
- Can be scaffolded now with stub nodes, refined as each agent is implemented
"""
