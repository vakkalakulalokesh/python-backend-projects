from __future__ import annotations

import re
import time
from typing import Any

import httpx

from app.tasks.base import BaseTask, TaskResult

_VAR_PATTERN = re.compile(r"\{\{\s*([^}]+?)\s*\}\}")


def _render_template(template: str, variables: dict[str, Any]) -> str:
    def repl(match: re.Match[str]) -> str:
        key = match.group(1).strip()
        val = variables.get(key, "")
        if isinstance(val, (dict, list)):
            return str(val)
        return str(val)

    return _VAR_PATTERN.sub(repl, template)


class HttpTask(BaseTask):
    @property
    def task_type(self) -> str:
        return "http"

    async def execute(self, config: dict, input_data: dict | None = None) -> TaskResult:
        start = time.perf_counter()
        inp = input_data or {}
        url = _render_template(str(config.get("url", "")), inp)
        method = str(config.get("method", "GET")).upper()
        headers = dict(config.get("headers") or {})
        body = config.get("body")
        if isinstance(body, str):
            body = _render_template(body, inp)
        json_payload = config.get("json")
        expected = set(config.get("expected_status_codes") or [200, 201, 204])
        timeout = float(config.get("timeout", 30))
        try:
            async with httpx.AsyncClient(timeout=timeout) as client:
                if json_payload is not None:
                    resp = await client.request(method, url, headers=headers, json=json_payload)
                else:
                    resp = await client.request(method, url, headers=headers, content=body)
            duration_ms = int((time.perf_counter() - start) * 1000)
            if resp.status_code not in expected:
                return TaskResult(
                    success=False,
                    output=None,
                    error=f"HTTP {resp.status_code}: {resp.text[:500]}",
                    duration_ms=duration_ms,
                )
            try:
                out: Any = resp.json()
            except Exception:
                out = resp.text
            return TaskResult(success=True, output=out, duration_ms=duration_ms)
        except Exception as e:
            duration_ms = int((time.perf_counter() - start) * 1000)
            return TaskResult(success=False, output=None, error=str(e), duration_ms=duration_ms)
