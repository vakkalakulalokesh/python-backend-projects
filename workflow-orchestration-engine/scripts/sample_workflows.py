from __future__ import annotations

"""
Seed sample workflows via the public HTTP API.
Usage: API_BASE=http://localhost:8000 python scripts/sample_workflows.py
"""

import os
import sys

import httpx

BASE = os.environ.get("API_BASE", "http://localhost:8000").rstrip("/")
API = f"{BASE}/api/v1"


def main() -> None:
    with httpx.Client(timeout=60.0) as client:
        headers = {"Content-Type": "application/json"}

        pipeline = {
            "name": "sample-data-pipeline",
            "description": "HTTP -> transform -> condition -> noop-delay",
            "created_by": "sample-script",
            "dag_definition": {
                "tasks": [
                    {"id": "fetch", "type": "http", "name": "Fetch", "config": {"url": "https://httpbin.org/json", "method": "GET"}},
                    {
                        "id": "shape",
                        "type": "transform",
                        "name": "Shape",
                        "config": {"transformations": {"has_slideshow": "bool(input.get('fetch', {}).get('slideshow'))"}},
                    },
                    {
                        "id": "branch",
                        "type": "condition",
                        "name": "Check",
                        "config": {"condition": "input.get('shape', {}).get('has_slideshow')", "on_true": "post", "on_false": "skip_end"},
                    },
                    {"id": "post", "type": "http", "name": "Post", "config": {"url": "https://httpbin.org/post", "method": "POST", "json": {"ok": True}}},
                    {"id": "skip_end", "type": "delay", "name": "Skipped path", "config": {"delay_seconds": 0.01}},
                ],
                "edges": [
                    {"from": "fetch", "to": "shape"},
                    {"from": "shape", "to": "branch"},
                    {"from": "branch", "to": "post"},
                    {"from": "branch", "to": "skip_end"},
                ],
            },
        }
        r = client.post(f"{API}/workflows", json=pipeline, headers=headers)
        r.raise_for_status()
        wf_id = r.json()["id"]
        print("Created pipeline workflow", wf_id)

        report = {
            "name": "sample-scheduled-report",
            "description": "Metrics -> aggregate -> delay (email stub)",
            "created_by": "sample-script",
            "dag_definition": {
                "tasks": [
                    {"id": "fetch_metrics", "type": "http", "name": "Metrics", "config": {"url": "https://httpbin.org/json", "method": "GET"}},
                    {"id": "aggregate", "type": "python", "name": "Aggregate", "config": {"expression": "{'keys': list(input.keys())}"}},
                    {"id": "report_wait", "type": "delay", "name": "Generate window", "config": {"delay_seconds": 0.05}},
                ],
                "edges": [
                    {"from": "fetch_metrics", "to": "aggregate"},
                    {"from": "aggregate", "to": "report_wait"},
                ],
            },
        }
        r = client.post(f"{API}/workflows", json=report, headers=headers)
        r.raise_for_status()
        report_id = r.json()["id"]
        print("Created report workflow", report_id)

        onboard = {
            "name": "sample-user-onboarding",
            "description": "Account -> welcome email -> short delay -> tutorial",
            "created_by": "sample-script",
            "dag_definition": {
                "tasks": [
                    {"id": "create", "type": "python", "name": "Create account", "config": {"expression": "{'user_id': 'u-123'}"}},
                    {"id": "welcome", "type": "http", "name": "Welcome", "config": {"url": "https://httpbin.org/post", "method": "POST", "json": {"template": "welcome"}}},
                    {"id": "wait_day", "type": "delay", "name": "Wait", "config": {"delay_seconds": 0.05}},
                    {"id": "tutorial", "type": "http", "name": "Tutorial", "config": {"url": "https://httpbin.org/post", "method": "POST", "json": {"template": "tutorial"}}},
                ],
                "edges": [
                    {"from": "create", "to": "welcome"},
                    {"from": "welcome", "to": "wait_day"},
                    {"from": "wait_day", "to": "tutorial"},
                ],
            },
        }
        r = client.post(f"{API}/workflows", json=onboard, headers=headers)
        r.raise_for_status()
        ob_id = r.json()["id"]
        print("Created onboarding workflow", ob_id)

        for label, wid in [("pipeline", wf_id), ("report", report_id), ("onboarding", ob_id)]:
            tr = client.post(f"{API}/workflows/{wid}/trigger", json={"input_data": {}}, headers=headers)
            tr.raise_for_status()
            print(f"Triggered {label}", tr.json())


if __name__ == "__main__":
    try:
        main()
    except httpx.HTTPError as e:
        print("HTTP error:", e, file=sys.stderr)
        sys.exit(1)
