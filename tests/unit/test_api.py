import pytest
from httpx import AsyncClient, ASGITransport
from app.main import app


@pytest.fixture
async def client():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


@pytest.mark.asyncio
async def test_health(client):
    resp = await client.get("/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"


@pytest.mark.asyncio
async def test_create_project(client):
    resp = await client.post(
        "/api/v1/projects/",
        json={"name": "Test Project", "niche": "business_tips"},
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["name"] == "Test Project"
    assert "id" in data
