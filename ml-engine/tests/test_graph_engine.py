"""
Synapse RiskOps - Graph Engine Test Suite
==========================================
Owner: Person 2 | Week: 3

Validates the NetworkX dependency graph engine:
- Graph construction from sample_dependencies.csv
- Upstream/downstream traversal correctness
- Blast radius calculations
- Root cause candidate ranking
- API endpoint integration
"""

from app.services.graph_builder import GraphBuilder
from app.schemas.graph import Criticality, ServiceType, DependencyType


def main():
    print("=" * 75)
    print("SYNAPSE RISKOPS - DEPENDENCY GRAPH ENGINE TEST SUITE")
    print("=" * 75)

    builder = GraphBuilder()
    summary = builder.build_graph()

    passed = 0
    failed = 0

    def check(name: str, condition: bool, detail: str = ""):
        nonlocal passed, failed
        if condition:
            passed += 1
            print(f"  PASS  {name}")
        else:
            failed += 1
            print(f"  FAIL  {name}  {detail}")

    # ===========================================================
    # Test 1: Graph Construction
    # ===========================================================
    print("\n" + "-" * 75)
    print("Test 1: Graph Construction")
    print("-" * 75)

    check("Node count = 12", summary["nodes"] == 12, f"got {summary['nodes']}")
    check("Edge count = 19", summary["edges"] == 19, f"got {summary['edges']}")
    check("api-gateway exists", "api-gateway" in builder.graph)
    check("postgres-primary exists", "postgres-primary" in builder.graph)

    # Verify edge: api-gateway -> auth-service
    check(
        "Edge api-gateway -> auth-service exists",
        builder.graph.has_edge("api-gateway", "auth-service"),
    )
    edge_data = builder.graph.edges["api-gateway", "auth-service"]
    check(
        "Edge type = SYNC",
        edge_data.get("dependency_type") == "SYNC",
        f"got {edge_data.get('dependency_type')}",
    )

    # Verify replication edge
    check(
        "Edge postgres-replica -> postgres-primary exists",
        builder.graph.has_edge("postgres-replica", "postgres-primary"),
    )
    rep_data = builder.graph.edges["postgres-replica", "postgres-primary"]
    check(
        "Replication edge type = REPLICATION",
        rep_data.get("dependency_type") == "REPLICATION",
        f"got {rep_data.get('dependency_type')}",
    )

    # ===========================================================
    # Test 2: Node Metadata
    # ===========================================================
    print("\n" + "-" * 75)
    print("Test 2: Node Metadata")
    print("-" * 75)

    pg_data = builder.graph.nodes["postgres-primary"]
    check("postgres-primary type = DATABASE", pg_data.get("service_type") == "DATABASE")
    check("postgres-primary criticality = CRITICAL", pg_data.get("criticality") == "CRITICAL")

    gw_data = builder.graph.nodes["api-gateway"]
    check("api-gateway type = GATEWAY", gw_data.get("service_type") == "GATEWAY")

    cache_data = builder.graph.nodes["cache-layer"]
    check("cache-layer type = INFRASTRUCTURE", cache_data.get("service_type") == "INFRASTRUCTURE")

    # ===========================================================
    # Test 3: Upstream Dependencies (api-gateway)
    # ===========================================================
    print("\n" + "-" * 75)
    print("Test 3: Upstream Dependencies (api-gateway)")
    print("-" * 75)

    gw_upstream = builder.get_upstream_dependencies("api-gateway")
    print(f"  api-gateway upstream: {gw_upstream}")

    # api-gateway directly depends on: auth, user, order, search
    check("auth-service in upstream", "auth-service" in gw_upstream)
    check("order-service in upstream", "order-service" in gw_upstream)
    # Transitive: order -> payment, order -> postgres, etc.
    check("postgres-primary in upstream (transitive)", "postgres-primary" in gw_upstream)
    check("payment-service in upstream (transitive)", "payment-service" in gw_upstream)
    check("cache-layer in upstream (transitive)", "cache-layer" in gw_upstream)

    # ===========================================================
    # Test 4: Upstream Dependencies (order-service)
    # ===========================================================
    print("\n" + "-" * 75)
    print("Test 4: Upstream Dependencies (order-service)")
    print("-" * 75)

    order_upstream = builder.get_upstream_dependencies("order-service")
    print(f"  order-service upstream: {order_upstream}")

    check("payment-service in upstream", "payment-service" in order_upstream)
    check("inventory-service in upstream", "inventory-service" in order_upstream)
    check("postgres-primary in upstream", "postgres-primary" in order_upstream)
    check("message-queue in upstream", "message-queue" in order_upstream)

    # ===========================================================
    # Test 5: Downstream Dependents (postgres-primary)
    # ===========================================================
    print("\n" + "-" * 75)
    print("Test 5: Downstream Dependents (postgres-primary)")
    print("-" * 75)

    pg_downstream = builder.get_downstream_dependents("postgres-primary")
    print(f"  postgres-primary downstream: {pg_downstream}")

    # These services directly or transitively depend on postgres
    check("auth-service depends on postgres", "auth-service" in pg_downstream)
    check("user-service depends on postgres", "user-service" in pg_downstream)
    check("order-service depends on postgres", "order-service" in pg_downstream)
    check("payment-service depends on postgres", "payment-service" in pg_downstream)
    check("inventory-service depends on postgres", "inventory-service" in pg_downstream)
    check("api-gateway depends on postgres (transitive)", "api-gateway" in pg_downstream)
    check("postgres-replica depends on postgres", "postgres-replica" in pg_downstream)

    # ===========================================================
    # Test 6: Blast Radius (postgres-primary)
    # ===========================================================
    print("\n" + "-" * 75)
    print("Test 6: Blast Radius (postgres-primary)")
    print("-" * 75)

    affected, score, paths = builder.get_blast_radius("postgres-primary")
    print(f"  Affected: {affected}")
    print(f"  Score: {score}%")
    print(f"  Paths: {paths}")

    check("Blast radius >= 7 services", len(affected) >= 7, f"got {len(affected)}")
    check("Blast radius score > 50%", score > 50, f"got {score}%")
    check("api-gateway affected", "api-gateway" in affected)

    # ===========================================================
    # Test 7: Blast Radius (cache-layer)
    # ===========================================================
    print("\n" + "-" * 75)
    print("Test 7: Blast Radius (cache-layer)")
    print("-" * 75)

    cache_affected, cache_score, _ = builder.get_blast_radius("cache-layer")
    print(f"  Affected: {cache_affected}")
    print(f"  Score: {cache_score}%")

    check("auth-service affected by cache failure", "auth-service" in cache_affected)
    check("search-service affected by cache failure", "search-service" in cache_affected)

    # ===========================================================
    # Test 8: Propagation Path
    # ===========================================================
    print("\n" + "-" * 75)
    print("Test 8: Propagation Path")
    print("-" * 75)

    path = builder.find_propagation_path("api-gateway", "postgres-primary")
    print(f"  api-gateway -> postgres-primary: {path}")
    check("Path exists", len(path) >= 2, f"got {path}")
    check("Path starts with api-gateway", path[0] == "api-gateway" if path else False)
    check("Path ends with postgres-primary", path[-1] == "postgres-primary" if path else False)

    # No path from postgres to api-gateway (wrong direction)
    no_path = builder.find_propagation_path("postgres-primary", "api-gateway")
    check("No reverse path postgres -> api-gateway", len(no_path) == 0, f"got {no_path}")

    # ===========================================================
    # Test 9: Root Cause Candidates (api-gateway)
    # ===========================================================
    print("\n" + "-" * 75)
    print("Test 9: Root Cause Candidates (api-gateway)")
    print("-" * 75)

    candidates = builder.rank_root_cause_candidates("api-gateway")
    print(f"  Candidates ({len(candidates)}):")
    for c in candidates:
        print(f"    {c.service_name:22s} | {c.criticality.value:8s} | {c.service_type.value:16s} | dist={c.distance}")

    check("Has candidates", len(candidates) > 0)

    # Top candidate should be CRITICAL + DATABASE/INFRASTRUCTURE
    top = candidates[0]
    check(
        "Top candidate is CRITICAL",
        top.criticality == Criticality.CRITICAL,
        f"got {top.criticality}",
    )

    # postgres-primary should be near the top (CRITICAL + DATABASE)
    pg_candidates = [c for c in candidates if c.service_name == "postgres-primary"]
    check("postgres-primary is a candidate", len(pg_candidates) > 0)

    # ===========================================================
    # Test 10: Root Cause Candidates (order-service)
    # ===========================================================
    print("\n" + "-" * 75)
    print("Test 10: Root Cause Candidates (order-service)")
    print("-" * 75)

    order_candidates = builder.rank_root_cause_candidates("order-service")
    print(f"  Candidates ({len(order_candidates)}):")
    for c in order_candidates:
        print(f"    {c.service_name:22s} | {c.criticality.value:8s} | dist={c.distance} | {c.dependency_type.value}")

    check("Has candidates", len(order_candidates) > 0)
    candidate_names = [c.service_name for c in order_candidates]
    check("payment-service is candidate", "payment-service" in candidate_names)
    check("postgres-primary is candidate", "postgres-primary" in candidate_names)

    # ===========================================================
    # Test 11: Edge Cases
    # ===========================================================
    print("\n" + "-" * 75)
    print("Test 11: Edge Cases")
    print("-" * 75)

    check("Unknown service returns empty upstream", builder.get_upstream_dependencies("nonexistent") == [])
    check("Unknown service returns empty downstream", builder.get_downstream_dependents("nonexistent") == [])
    check("Unknown service returns empty candidates", builder.rank_root_cause_candidates("nonexistent") == [])
    check("Unknown path returns empty", builder.find_propagation_path("nonexistent", "api-gateway") == [])

    # Leaf node (notification-svc only depends on message-queue)
    notif_upstream = builder.get_upstream_dependencies("notification-svc")
    check("notification-svc upstream = [message-queue]", notif_upstream == ["message-queue"])

    # ===========================================================
    # Test 12: get_all_nodes and get_all_edges
    # ===========================================================
    print("\n" + "-" * 75)
    print("Test 12: Full Topology Export")
    print("-" * 75)

    all_nodes = builder.get_all_nodes()
    all_edges = builder.get_all_edges()
    check("get_all_nodes returns 12", len(all_nodes) == 12, f"got {len(all_nodes)}")
    check("get_all_edges returns 19", len(all_edges) == 19, f"got {len(all_edges)}")

    # Verify NodeSchema fields
    gw_node = [n for n in all_nodes if n.service_name == "api-gateway"][0]
    check("api-gateway in_degree >= 0", gw_node.in_degree >= 0)
    check("api-gateway out_degree = 4", gw_node.out_degree == 4, f"got {gw_node.out_degree}")

    # ===========================================================
    # Summary
    # ===========================================================
    print("\n" + "=" * 75)
    print("TEST SUMMARY")
    print("=" * 75)
    total = passed + failed
    print(f"  Passed: {passed}/{total}")
    print(f"  Failed: {failed}/{total}")
    if failed == 0:
        print("  ALL TESTS PASSED!")
    else:
        print(f"  {failed} test(s) FAILED")


if __name__ == "__main__":
    main()
