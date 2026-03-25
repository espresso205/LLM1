"""
集成测试：推理接口 + 重试接口（async httpx + 内存数据库）。
"""
import pytest

pytestmark = pytest.mark.anyio


class TestSubmitInference:
    async def test_submit_returns_200(self, client):
        resp = await client.post("/api/v1/inference", json={
            "prompt": "hello", "max_tokens": 128, "temperature": 0.5,
        })
        assert resp.status_code == 200

    async def test_submit_response_shape(self, client):
        resp = await client.post("/api/v1/inference", json={"prompt": "hi"})
        body = resp.json()
        assert "request_id" in body
        assert "result" in body
        assert body["status"] == "success"
        assert "created_at" in body

    async def test_submit_empty_prompt_is_rejected(self, client):
        resp = await client.post("/api/v1/inference", json={"prompt": ""})
        assert resp.status_code == 422

    async def test_submit_persists_to_history(self, client):
        await client.post("/api/v1/inference", json={"prompt": "stored?"})
        resp = await client.get("/api/v1/history")
        assert resp.json()["total"] >= 1


class TestGetHistory:
    async def test_empty_history(self, client):
        resp = await client.get("/api/v1/history")
        assert resp.status_code == 200
        body = resp.json()
        assert body["items"] == []
        assert body["total"] == 0

    async def test_history_contains_submitted(self, client):
        await client.post("/api/v1/inference", json={"prompt": "track me"})
        resp = await client.get("/api/v1/history")
        body = resp.json()
        assert body["total"] == 1
        assert "track me" in body["items"][0]["prompt_preview"]

    async def test_status_filter(self, client):
        await client.post("/api/v1/inference", json={"prompt": "ok"})
        resp = await client.get("/api/v1/history", params={"status": "success"})
        assert resp.json()["total"] == 1
        resp2 = await client.get("/api/v1/history", params={"status": "failed"})
        assert resp2.json()["total"] == 0

    async def test_pagination(self, client):
        for i in range(5):
            await client.post("/api/v1/inference", json={"prompt": f"p{i}"})
        resp = await client.get("/api/v1/history", params={"limit": 2, "offset": 0})
        body = resp.json()
        assert body["total"] == 5
        assert len(body["items"]) == 2


class TestGetHistoryDetail:
    async def test_detail_404_for_missing(self, client):
        resp = await client.get("/api/v1/history/nonexistent-id")
        assert resp.status_code == 404

    async def test_detail_returns_full_fields(self, client):
        sub = (await client.post("/api/v1/inference", json={
            "prompt": "detail test", "max_tokens": 64, "temperature": 1.0,
        })).json()

        resp = await client.get(f"/api/v1/history/{sub['request_id']}")
        assert resp.status_code == 200
        body = resp.json()
        assert body["request_id"] == sub["request_id"]
        assert body["prompt"] == "detail test"
        assert body["max_tokens"] == 64
        assert body["temperature"] == 1.0
        assert "result" in body
        assert "duration_ms" in body


class TestRetryInference:
    async def test_retry_404_for_missing(self, client):
        resp = await client.post("/api/v1/inference/bad-id/retry")
        assert resp.status_code == 404

    async def test_retry_creates_new_record(self, client):
        sub = (await client.post("/api/v1/inference", json={"prompt": "retry me"})).json()

        retry_resp = await client.post(f"/api/v1/inference/{sub['request_id']}/retry")
        assert retry_resp.status_code == 200
        assert retry_resp.json()["request_id"] != sub["request_id"]

    async def test_retry_uses_same_prompt(self, client):
        sub = (await client.post("/api/v1/inference", json={"prompt": "same prompt"})).json()
        retry = (await client.post(f"/api/v1/inference/{sub['request_id']}/retry")).json()

        detail = (await client.get(f"/api/v1/history/{retry['request_id']}")).json()
        assert detail["prompt"] == "same prompt"

    async def test_retry_increments_total(self, client):
        sub = (await client.post("/api/v1/inference", json={"prompt": "count"})).json()
        await client.post(f"/api/v1/inference/{sub['request_id']}/retry")

        resp = await client.get("/api/v1/history")
        assert resp.json()["total"] == 2
