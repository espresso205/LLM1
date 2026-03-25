"""
单元测试：异步 store 层的 CRUD 操作。
"""
import uuid
from datetime import datetime, timezone

import pytest

from app import store
from app.models import RequestRecord

pytestmark = pytest.mark.anyio


def _make_record(**kwargs) -> RequestRecord:
    defaults = dict(
        request_id=str(uuid.uuid4()),
        prompt="test prompt",
        max_tokens=256,
        temperature=0.5,
        result="test result",
        status="success",
        created_at=datetime.now(timezone.utc),
        duration_ms=10,
    )
    defaults.update(kwargs)
    return RequestRecord(**defaults)


class TestSave:
    async def test_save_returns_record(self, db_session):
        r = _make_record()
        saved = await store.save(db_session, r)
        assert saved.id is not None
        assert saved.request_id == r.request_id

    async def test_save_persists_to_db(self, db_session):
        r = _make_record(prompt="hello world")
        await store.save(db_session, r)
        fetched = await store.get_by_request_id(db_session, r.request_id)
        assert fetched is not None
        assert fetched.prompt == "hello world"


class TestListRecords:
    async def test_empty_db_returns_zero_total(self, db_session):
        rows, total = await store.list_records(db_session)
        assert rows == []
        assert total == 0

    async def test_returns_all_records(self, db_session):
        for _ in range(3):
            await store.save(db_session, _make_record())
        rows, total = await store.list_records(db_session, limit=10)
        assert total == 3
        assert len(rows) == 3

    async def test_limit_respected(self, db_session):
        for _ in range(5):
            await store.save(db_session, _make_record())
        rows, total = await store.list_records(db_session, limit=2)
        assert total == 5
        assert len(rows) == 2

    async def test_offset_respected(self, db_session):
        for _ in range(4):
            await store.save(db_session, _make_record())
        rows_p1, _ = await store.list_records(db_session, limit=2, offset=0)
        rows_p2, _ = await store.list_records(db_session, limit=2, offset=2)
        ids_p1 = {r.request_id for r in rows_p1}
        ids_p2 = {r.request_id for r in rows_p2}
        assert ids_p1.isdisjoint(ids_p2)

    async def test_status_filter_success(self, db_session):
        await store.save(db_session, _make_record(status="success"))
        await store.save(db_session, _make_record(status="failed"))
        rows, total = await store.list_records(db_session, status="success")
        assert total == 1
        assert rows[0].status == "success"

    async def test_status_filter_failed(self, db_session):
        await store.save(db_session, _make_record(status="success"))
        await store.save(db_session, _make_record(status="failed"))
        rows, total = await store.list_records(db_session, status="failed")
        assert total == 1
        assert rows[0].status == "failed"

    async def test_ordered_by_created_at_desc(self, db_session):
        from datetime import timedelta
        now = datetime.now(timezone.utc)
        r_old = _make_record(created_at=now - timedelta(hours=1))
        r_new = _make_record(created_at=now)
        await store.save(db_session, r_old)
        await store.save(db_session, r_new)
        rows, _ = await store.list_records(db_session)
        assert rows[0].request_id == r_new.request_id


class TestGetByRequestId:
    async def test_returns_none_for_missing(self, db_session):
        assert await store.get_by_request_id(db_session, "nonexistent") is None

    async def test_returns_correct_record(self, db_session):
        r = _make_record(prompt="find me")
        await store.save(db_session, r)
        found = await store.get_by_request_id(db_session, r.request_id)
        assert found is not None
        assert found.prompt == "find me"
