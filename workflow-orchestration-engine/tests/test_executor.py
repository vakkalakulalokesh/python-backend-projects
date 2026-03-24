from __future__ import annotations

import pytest

from app.tasks.condition_task import ConditionTask
from app.tasks.delay_task import DelayTask
from app.tasks.http_task import HttpTask


@pytest.mark.asyncio
async def test_delay_task() -> None:
    t = DelayTask()
    r = await t.execute({"delay_seconds": 0.01}, {})
    assert r.success
    assert r.output["delayed_seconds"] == 0.01


@pytest.mark.asyncio
async def test_condition_task() -> None:
    t = ConditionTask()
    r = await t.execute(
        {"condition": "input.get('x') > 1", "on_true": "t1", "on_false": "t2"},
        {"x": 2},
    )
    assert r.success
    assert r.output["result"] is True
    assert r.output["next_task_id"] == "t1"


@pytest.mark.asyncio
async def test_http_task_mocked(monkeypatch: pytest.MonkeyPatch) -> None:
    class FakeResp:
        status_code = 200
        text = "ok"

        def json(self) -> dict:
            return {"ok": True}

    class FakeClient:
        def __init__(self, *a, **k) -> None:
            pass

        async def __aenter__(self) -> "FakeClient":
            return self

        async def __aexit__(self, *a) -> None:
            pass

        async def request(self, *a, **k) -> FakeResp:
            return FakeResp()

    import httpx

    monkeypatch.setattr(httpx, "AsyncClient", FakeClient)
    t = HttpTask()
    r = await t.execute({"url": "https://example.com", "method": "GET"}, {})
    assert r.success
    assert r.output == {"ok": True}
