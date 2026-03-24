# Real-Time Anomaly Detection & Metrics Intelligence Platform

Production-grade observability-style service that ingests application and infrastructure metrics, scores each point against a **multi-algorithm detection ensemble** in near real time, persists state in PostgreSQL, keeps rolling windows in Redis, decouples workloads with Kafka, and pushes alerts over **WebSockets** plus optional webhooks.

## Architecture

```
Metric Sources ──► FastAPI (Ingest) ──► Kafka [metrics.raw]
                        │                      │
                        ▼                      ▼
                   PostgreSQL            Kafka Consumer
                  (persistence)               │
                        │              ┌──────┴──────┐
                        │              │  Detection   │
                        │              │   Engine     │
                        │              └──────┬──────┘
                        │                     │
                        │         ┌───────────┼───────────┐
                        │         ▼           ▼           ▼
                        │    Z-Score      IQR/MAD     Isolation
                        │    EWMA       Seasonal      Forest
                        │         └───────────┬───────────┘
                        │                     │
                        │              ┌──────▼──────┐
                        │              │  Anomaly    │
                        ▼              │  Service    │
                   Redis Cache         └──────┬──────┘
                 (sliding windows,           │
                  cooldowns,          ┌──────┴──────┐
                  counters)           ▼              ▼
                              WebSocket Alert   Notification
                              (real-time)       (webhook/email)
```

HTTP ingest writes to Postgres and Redis, publishes to `metrics.ingested`, and runs the detection engine inline for minimal latency. External agents can publish to **`metrics.raw`**; the background consumer updates Redis and runs the same engine.

## Anomaly detection algorithms

| Algorithm | Method | Best for | Cost |
|-----------|--------|----------|------|
| Z-Score | Mean / std deviation | Gaussian-ish metrics, quick spikes | Very low |
| IQR | Quartile fences | Skewed distributions, robust to tails | Low |
| MAD | Median absolute deviation | Heavy-tailed series, outlier contamination | Low |
| EWMA | Exponentially weighted mean/var | Gradual drift, smooth trends | Low |
| Seasonal | Moving trend + seasonal residual | Daily/weekly cycles | Medium |
| Isolation Forest | Random partition trees | Nonlinear, multivariate-like windows | Medium |

## Tech stack

- **Python 3.11**, **FastAPI**, **Uvicorn**
- **SQLAlchemy 2.0** (async) + **Alembic** + **PostgreSQL** (JSONB, UUID)
- **Pydantic v2** + **pydantic-settings**
- **Redis** (sorted-set sliding windows, cooldown keys, counters)
- **Kafka** (**aiokafka**) for `metrics.raw`, `metrics.ingested`, `anomalies.detected`
- **Celery** + Redis for batch detection and retention jobs
- **NumPy / SciPy / scikit-learn** for detectors
- **httpx** for outbound webhooks
- **WebSockets** for live alert fan-out

## API quick reference

Base URL: `http://localhost:8000`

### Ingest

```bash
curl -s -X POST http://localhost:8000/api/v1/metrics/ingest \
  -H "Content-Type: application/json" \
  -d '{"source_name":"api-1","metric_name":"cpu.util","value":87.2,"unit":"percent"}'
```

### Batch ingest

```bash
curl -s -X POST http://localhost:8000/api/v1/metrics/ingest/batch \
  -H "Content-Type: application/json" \
  -d '{"metrics":[{"source_name":"api-1","metric_name":"cpu.util","value":40},{"source_name":"api-1","metric_name":"cpu.util","value":120}]}'
```

### Query & aggregation

```bash
curl -s "http://localhost:8000/api/v1/metrics/query?source_name=api-1&metric_name=cpu.util&start_time=2025-03-01T00:00:00Z&end_time=2025-03-24T23:59:59Z"

curl -s "http://localhost:8000/api/v1/metrics/aggregation?source_name=api-1&metric_name=cpu.util&start_time=2025-03-01T00:00:00Z&end_time=2025-03-24T23:59:59Z"
```

### Anomalies

```bash
curl -s "http://localhost:8000/api/v1/anomalies?page=1&size=20&severity=high"
curl -s http://localhost:8000/api/v1/anomalies/stats
```

### Alert rules

```bash
curl -s -X POST http://localhost:8000/api/v1/rules \
  -H "Content-Type: application/json" \
  -d '{"name":"cpu-high-zscore","detector_type":"zscore","severity_threshold":"medium","notification_channels":[{"type":"webhook","url":"https://example.com/hook"}]}'
```

### Dashboard

```bash
curl -s http://localhost:8000/api/v1/dashboard/overview
curl -s http://localhost:8000/api/v1/dashboard/timeline?hours=48
```

### WebSocket alerts

Connect to `ws://localhost:8000/ws/alerts` (optional query `?source_id=<uuid>` to filter by source).

## How to run

1. Copy `.env.example` to `.env` and adjust URLs for local or Docker hostnames.
2. **Docker Compose** (recommended):

   ```bash
   docker compose up --build
   ```

   Migrations run before Uvicorn starts. API: `http://localhost:8000`, health: `GET /health`.

3. **Local** (Postgres + Redis + Kafka required):

   ```bash
   python -m venv .venv && source .venv/bin/activate
   pip install -r requirements.txt
   pip install pytest pytest-asyncio   # optional, for tests
   alembic upgrade head
   uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
   ```

4. **Sample load**:

   ```bash
   pip install httpx   # if not already installed
   python scripts/generate_sample_metrics.py
   ```

## System design notes

- **Why multiple detectors**: Each method has different failure modes; an ensemble reduces blind spots (e.g. IQR vs Gaussian assumptions, EWMA vs sudden spikes, seasonal vs drift).
- **Redis sliding windows**: Per `(source_id, metric)` sorted sets give ordered recent values with bounded cardinality for O(window) reads.
- **Kafka**: Ingest and detection can scale independently; `metrics.raw` supports agents that do not speak HTTP.
- **Celery**: Periodic batch reprocessing (`run_batch_detection`) and retention (`cleanup_old_metrics`, `cleanup_resolved_anomalies`) keep the hot path thin.
- **Cooldowns**: Per-detector Redis keys throttle duplicate `AnomalyRecord` rows; rule-level keys throttle notification storms.
- **Horizontal scaling**: Stateless API + consumer group for `metrics.raw`; shared Postgres, Redis, and Kafka; WebSocket fan-out requires sticky sessions or a shared pub/sub layer in a full multi-node deployment.

## Tests

```bash
pip install pytest pytest-asyncio
pytest tests/test_detectors.py -q
RUN_INTEGRATION=1 pytest tests/test_metric_service.py -q   # needs Postgres + Redis + DB anomaly_test
```

## Future enhancements

- Grafana / Prometheus remote-write ingestion
- Pluggable detector registry with dynamic config
- Auto-threshold tuning from historical false-positive rate
- Correlation with OpenTelemetry trace IDs for root-cause hints

## License

MIT (adjust for your organization as needed).
