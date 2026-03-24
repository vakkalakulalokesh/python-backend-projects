#!/usr/bin/env python3
"""
Push synthetic host metrics to the anomaly-detection API with occasional spikes.
Usage:
  export API_BASE=http://localhost:8000
  python scripts/generate_sample_metrics.py
"""

import asyncio
import os
import random
from datetime import datetime, timezone

import httpx

API_BASE = os.environ.get("API_BASE", "http://localhost:8000").rstrip("/")
SOURCE = os.environ.get("SAMPLE_SOURCE", "demo-host-01")


async def main() -> None:
    rng = random.Random(42)
    async with httpx.AsyncClient(base_url=API_BASE, timeout=30.0) as client:
        for i in range(200):
            ts = datetime.now(timezone.utc)
            cpu = rng.gauss(35, 4)
            mem = rng.gauss(62, 3)
            disk = rng.gauss(55, 2)
            net_in = max(0.0, rng.gauss(120, 20))
            if i % 37 == 0:
                cpu += 55
                mem += 25
            if i % 53 == 0:
                disk = 98.5
            metrics = [
                {"source_name": SOURCE, "metric_name": "cpu.utilization", "value": cpu, "unit": "percent"},
                {"source_name": SOURCE, "metric_name": "memory.utilization", "value": mem, "unit": "percent"},
                {"source_name": SOURCE, "metric_name": "disk.utilization", "value": disk, "unit": "percent"},
                {"source_name": SOURCE, "metric_name": "network.in", "value": net_in, "unit": "mbps"},
            ]
            for m in metrics:
                m["timestamp"] = ts.isoformat()
            r = await client.post("/api/v1/metrics/ingest/batch", json={"metrics": metrics})
            r.raise_for_status()
            await asyncio.sleep(0.15)
    print(f"Sent sample metrics to {API_BASE} for source {SOURCE}")


if __name__ == "__main__":
    asyncio.run(main())
