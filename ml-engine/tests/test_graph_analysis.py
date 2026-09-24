"""
Tests for Advanced NetworkX Graph Analysis
(PageRank, Centrality, Cascade Simulation, Root Cause Correlation).
"""

import sys
from pathlib import Path
import pytest
from fastapi.testclient import TestClient

ML_ENGINE_ROOT = Path(__file__).resolve().parent.parent
if str(ML_ENGINE_ROOT) not in sys.path:
    sys.path.insert(0, str(ML_ENGINE_ROOT))

from app.services.graph_builder import get_graph_builder, GraphBuilder
from app.main import app


@pytest.fixture
def graph_builder():
    builder = get_graph_builder()
    if not builder.is_built:
        builder.build_graph()
    return builder


@pytest.fixture
def client():
    return TestClient(app)


def test_pagerank_calculation(graph_builder):
    pagerank = graph_builder.calculate_pagerank()
    assert len(pagerank) == 12
    assert "postgres-primary" in pagerank
    assert "api-gateway" in pagerank
    # Sum of PageRank scores across graph ~ 1.0
    total = sum(pagerank.values())
    assert 0.95 <= total <= 1.05


def test_betweenness_centrality(graph_builder):
    centrality = graph_builder.calculate_betweenness_centrality()
    assert len(centrality) == 12
    # At least some nodes should have positive betweenness centrality
    assert any(score > 0 for score in centrality.values())


def test_simulate_cascade(graph_builder):
    sim = graph_builder.simulate_cascade("postgres-primary")
    assert sim["root_failure"] == "postgres-primary"
    assert sim["total_impacted_services"] > 0
    assert len(sim["timeline"]) > 0
    assert sim["timeline"][0]["service_name"] == "postgres-primary"
    assert sim["timeline"][0]["propagation_depth"] == 0


def test_find_common_root_cause(graph_builder):
    candidates = graph_builder.find_common_root_cause(["order-service", "payment-service"])
    assert len(candidates) > 0
    names = [c["service_name"] for c in candidates]
    assert "postgres-primary" in names


def test_api_root_cause_analysis(client):
    response = client.get("/api/graph/root-cause-analysis?services=order-service,payment-service")
    assert response.status_code == 200
    data = response.json()
    assert "alerting_services" in data
    assert "root_cause_candidates" in data
    assert len(data["root_cause_candidates"]) > 0


def test_api_critical_paths(client):
    response = client.get("/api/graph/critical-paths")
    assert response.status_code == 200
    data = response.json()
    assert "total_nodes" in data
    assert "bottleneck_services" in data
    assert data["total_nodes"] == 12


def test_api_cascade_simulation(client):
    response = client.get("/api/graph/cascade-simulation?failing_service=postgres-primary")
    assert response.status_code == 200
    data = response.json()
    assert "cascade_timeline" in data
    assert len(data["cascade_timeline"]) > 0
