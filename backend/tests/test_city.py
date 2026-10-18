"""
tests/test_city.py
------------------
Tests for the city graph and metadata endpoints.
"""

import pytest


@pytest.mark.asyncio
async def test_city_metadata_200(async_client):
    response = await async_client.get("/api/v1/city/metadata")
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_city_metadata_fields(async_client):
    response = await async_client.get("/api/v1/city/metadata")
    data = response.json()
    assert data["district"] == "Bengaluru Urban"
    assert data["state"] == "Karnataka"
    assert data["country"] == "India"
    assert "bbox" in data
    assert "crs" in data


@pytest.mark.asyncio
async def test_city_graph_200(async_client):
    response = await async_client.get("/api/v1/city/graph")
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_city_graph_has_nodes_and_edges(async_client):
    response = await async_client.get("/api/v1/city/graph")
    data = response.json()
    assert "nodes" in data
    assert "edges" in data
    assert "metadata" in data
    assert len(data["nodes"]) > 0
    assert len(data["edges"]) > 0


@pytest.mark.asyncio
async def test_city_graph_node_structure(async_client):
    response = await async_client.get("/api/v1/city/graph")
    nodes = response.json()["nodes"]
    node = nodes[0]
    assert "node_id" in node
    assert "lat" in node
    assert "lon" in node
    assert "node_type" in node
    # Coordinates must be within Bengaluru Urban approximate bounds
    assert 12.7 <= node["lat"] <= 13.3
    assert 77.2 <= node["lon"] <= 77.9


@pytest.mark.asyncio
async def test_city_graph_edge_structure(async_client):
    response = await async_client.get("/api/v1/city/graph")
    edges = response.json()["edges"]
    edge = edges[0]
    assert "edge_id" in edge
    assert "source_node" in edge
    assert "target_node" in edge
    assert "status" in edge
    assert edge["status"] in ("OPEN", "DEGRADED", "CLOSED")
    assert "travel_time_s" in edge
    assert edge["travel_time_s"] >= 0


@pytest.mark.asyncio
async def test_city_graph_has_hospital_nodes(async_client):
    """The bundled graph must include at least one hospital node."""
    response = await async_client.get("/api/v1/city/graph")
    nodes = response.json()["nodes"]
    hospital_nodes = [n for n in nodes if n["node_type"] == "hospital"]
    assert len(hospital_nodes) >= 1
