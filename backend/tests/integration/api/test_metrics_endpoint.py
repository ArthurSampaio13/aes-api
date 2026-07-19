import pytest


@pytest.mark.asyncio
async def test_metrics_endpoint_exposes_prometheus_format(client):
    response = await client.get("/metrics")
    assert response.status_code == 200
    assert b"# HELP" in response.content
