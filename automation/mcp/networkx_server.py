"""
Synapse RiskOps - NetworkX & Graph Analysis MCP Server
Provides graph topology analysis, centrality calculations, and cascade simulation.
"""

from mcp.server.fastmcp import FastMCP
import networkx as nx

mcp = FastMCP("networkx-analyzer")

def _parse_edges(edge_list: list[str]) -> nx.DiGraph:
    g = nx.DiGraph()
    for item in edge_list:
        item = item.strip()
        if "->" in item:
            u, v = item.split("->", 1)
            g.add_edge(u.strip(), v.strip())
        elif "," in item:
            u, v = item.split(",", 1)
            g.add_edge(u.strip(), v.strip())
        elif " " in item:
            parts = item.split()
            if len(parts) >= 2:
                g.add_edge(parts[0], parts[1])
    return g

@mcp.tool()
def analyze_topology(edges: list[str]) -> dict:
    """
    Analyze dependency graph topology between services using NetworkX.
    Takes a list of directed edges, e.g. ["frontend->backend", "backend->postgres"].
    Returns node count, edge count, PageRank scores, and betweenness centrality.
    """
    g = _parse_edges(edges)

    if len(g.nodes) == 0:
        return {"error": "Empty or unparseable graph provided"}

    pagerank = nx.pagerank(g) if len(g) > 1 else {n: 1.0 for n in g.nodes}
    betweenness = nx.betweenness_centrality(g)
    in_degrees = dict(g.in_degree())
    out_degrees = dict(g.out_degree())

    return {
        "nodes": list(g.nodes()),
        "node_count": g.number_of_nodes(),
        "edge_count": g.number_of_edges(),
        "pagerank_ranking": sorted(pagerank.items(), key=lambda x: x[1], reverse=True),
        "betweenness_centrality": betweenness,
        "in_degrees": in_degrees,
        "out_degrees": out_degrees,
    }

@mcp.tool()
def simulate_cascading_failure(edges: list[str], failed_service: str) -> dict:
    """
    Simulate impact radius when a specific service fails.
    Takes a list of directed edges, e.g. ["frontend->backend", "backend->postgres"]
    and the name of the failed service.
    Returns all downstream impacted services and blast radius score.
    """
    g = _parse_edges(edges)

    if failed_service not in g:
        return {"error": f"Service '{failed_service}' not found in dependency graph"}

    downstream = list(nx.ancestors(g, failed_service))
    upstream_deps = list(nx.descendants(g, failed_service))

    return {
        "failed_service": failed_service,
        "directly_impacted_callers": list(g.predecessors(failed_service)),
        "all_downstream_impacted_services": downstream,
        "upstream_dependencies": upstream_deps,
        "blast_radius_score": len(downstream) / max(1, g.number_of_nodes()),
    }

if __name__ == "__main__":
    mcp.run()
