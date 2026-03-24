# Distributed Workflow Orchestration Engine

A production-grade workflow orchestration engine inspired by Temporal and Apache Airflow, providing DAG-based workflow definition, distributed execution via Celery, cron scheduling, Redis-backed coordination, and real-time execution monitoring over WebSockets.

## Architecture

```
                    ┌─────────────────────────────────┐
                    │          FastAPI Server          │
                    │  ┌──────────┐ ┌──────────────┐  │
  REST API ────────►│  │ Workflow │ │  Execution   │  │
                    │  │   CRUD   │ │   Tracking   │  │
  WebSocket ◄──────│  └──────────┘ └──────┬───────┘  │
                    │                      │          │
                    └──────────────────────┼──────────┘
                                           │ trigger
                                           ▼
                    ┌─────────────────────────────────┐
                    │        Celery Workers            │
                    │  ┌──────────┐ ┌──────────────┐  │
                    │  │ Workflow │ │   Schedule    │  │
                    │  │ Executor │ │   Checker     │  │
                    │  └────┬─────┘ └──────────────┘  │
                    │       │                          │
                    │  ┌────▼──────────────────────┐  │
                    │  │      DAG Engine            │  │
                    │  │  ┌─────┐ ┌─────┐ ┌─────┐  │  │
                    │  │  │HTTP │ │Cond │ │Xform│  │  │
                    │  │  │Task │ │Task │ │Task │  │  │
                    │  │  └─────┘ └─────┘ └─────┘  │  │
                    │  └───────────────────────────┘  │
                    └──────────────────────────────────┘
                              │           │
                    ┌─────────▼─┐   ┌─────▼─────┐
                    │PostgreSQL │   │   Redis    │
                    │(workflows,│   │(locks,     │
                    │executions)│   │ cache,     │
                    │           │   │ broker)    │
                    └───────────┘   └───────────┘
```

## Workflow definition (JSON DAG)

Workflows are versioned definitions with a JSON DAG: `tasks` (nodes) and `edges` (dependencies). Each task has a `type`, human-readable `name`, opaque `config`, and optional `retry` / `timeout_seconds`.

```json
{
  "tasks": [
    {
      "id": "fetch",
      "type": "http",
      "name": "Fetch data",
      "config": { "url": "https://api.example.com/data", "method": "GET" },
      "retry": { "max_attempts": 3, "strategy": "exponential", "delay_seconds": 2, "max_delay_seconds": 120 }
    },
    { "id": "normalize", "type": "transform", "name": "Normalize", "config": { "transformations": { "id": "input.get('fetch', {}).get('id')" } } },
    { "id": "gate", "type": "condition", "name": "Branch", "config": { "condition": "bool(input.get('normalize', {}).get('id'))", "on_true": "downstream_ok", "on_false": "downstream_skip" } },
    { "id": "downstream_ok", "type": "delay", "name": "Continue", "config": { "delay_seconds": 0.05 } },
    { "id": "downstream_skip", "type": "delay", "name": "Alt", "config": { "delay_seconds": 0.01 } }
  ],
  "edges": [
    { "from": "fetch", "to": "normalize" },
    { "from": "normalize", "to": "gate" },
    { "from": "gate", "to": "downstream_ok" },
    { "from": "gate", "to": "downstream_skip" }
  ]
}
```

Task inputs merge workflow trigger `input_data`, outputs of completed predecessor tasks (keyed by task id), and a `tasks` map of predecessor outputs for convenience.

## Available task types

| Type | Description | Config highlights | Example |
|------|-------------|-------------------|---------|
| `http` | HTTP call via httpx | `url`, `method`, `headers`, `body` or `json`, `expected_status_codes`, `timeout` | `{"url": "https://httpbin.org/get", "method": "GET"}` |
| `python` | Restricted expression over `input` | `expression` | `{"expression": "{'sum': sum(input.get('values', []))}"}` |
| `delay` | `asyncio.sleep` for pacing | `delay_seconds` | `{"delay_seconds": 5}` |
| `condition` | Boolean branch metadata | `condition`, `on_true`, `on_false` | See DAG example above |
| `transform` | Per-key Python expressions | `transformations` map | `{"transformations": {"full_name": "input.get('a','') + ' ' + input.get('b','')"}}` |

## Execution lifecycle

States: `pending` → `running` → `completed` | `failed` | `cancelled` | `timed_out`. Retries may move `failed` / `timed_out` back toward `pending` at the task level; workflow-level `retry` re-queues the execution via the API.

```mermaid
stateDiagram-v2
    [*] --> pending
    pending --> running
    running --> completed
    running --> failed
    running --> cancelled
    running --> timed_out
    failed --> pending
    timed_out --> pending
    completed --> [*]
    cancelled --> [*]
```

## Retry strategies

| Strategy | Behavior | When to use |
|----------|----------|-------------|
| `fixed` | Constant delay | Predictable backoff, simple retries |
| `exponential` | Base × 2^(attempt−1), optional jitter | Unstable downstream, thundering herd mitigation |
| `linear` | initial + increment × (attempt−1) | Steady ramp without explosion |

## Cron scheduling

`WorkflowSchedule` stores a cron expression (evaluated with `croniter`), timezone label (stored; execution uses UTC baselines in the checker), optional default `input_data`, and `next_run_at`. Celery Beat invokes `check_schedules`, which acquires a Redis lock per schedule row to avoid duplicate triggers under multiple beat workers.

## API quick reference (curl)

Create a workflow:

```bash
curl -s -X POST http://localhost:8000/api/v1/workflows \
  -H 'Content-Type: application/json' \
  -d '{"name":"demo","created_by":"alice","dag_definition":{"tasks":[{"id":"t1","type":"delay","name":"Wait","config":{"delay_seconds":0.05}}],"edges":[]}}'
```

Trigger:

```bash
curl -s -X POST http://localhost:8000/api/v1/workflows/<WORKFLOW_UUID>/trigger \
  -H 'Content-Type: application/json' \
  -d '{"input_data":{"region":"us-east-1"},"triggered_by":"manual"}'
```

Check execution:

```bash
curl -s http://localhost:8000/api/v1/executions/<EXECUTION_UUID>
```

WebSocket (browser or `wscat`):

```text
ws://localhost:8000/ws/executions
```

OpenAPI docs: `http://localhost:8000/docs`

## How to run

**Docker Compose (recommended)**

```bash
cp .env.example .env
docker compose up --build
```

Services: `app` (FastAPI + Alembic migrate on start), `postgres`, `redis`, `celery-worker`, `celery-beat`.

**Local (Python 3.9+)**

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
export DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5432/workflow_db
export REDIS_URL=redis://localhost:6379/0
export CELERY_BROKER_URL=redis://localhost:6379/1
alembic upgrade head
uvicorn app.main:app --reload
# separate terminals:
celery -A app.workers.celery_app worker --loglevel=info
celery -A app.workers.celery_app beat --loglevel=info
```

**Sample data**

```bash
pip install httpx
API_BASE=http://localhost:8000 python scripts/sample_workflows.py
```

## System design deep dive

- **DAG validation** — Tasks and edges are loaded into a `networkx.DiGraph`. Validation enforces acyclicity (`nx.is_directed_acyclic_graph`), referential integrity on edges, and at least one root. Topological generations expose parallel waves.
- **Distributed execution** — API persists a `WorkflowExecution` and dispatches `execute_workflow_task` to Celery. The worker runs an asyncio event loop, executes tasks with a semaphore (`MAX_CONCURRENT_TASKS`), and persists `TaskExecution` rows.
- **Schedule safety** — Redis `SET NX` locks per schedule id guard concurrent beat/worker pairs.
- **State machine** — `ExecutionStateMachine` centralizes allowed transitions for workflow status.
- **Retries** — Pluggable strategies (`fixed`, `exponential` with jitter, `linear`) compute delays between task attempts; task-level `max_attempts` comes from DAG JSON or global defaults.
- **Correlation** — `correlation_id` on executions supports idempotent tracing (e.g. schedule id or external request id).
- **Horizontal scaling** — Scale stateless FastAPI replicas behind a load balancer; scale Celery workers independently; use a single PostgreSQL primary and Redis for broker/cache/locks; WebSocket clients should stick to one replica or introduce a shared pub/sub fan-out (this codebase publishes execution events to Redis and the API subscribes to fan-in to local WebSocket connections).

## Sample workflows (real-world patterns)

1. **Data pipeline** — HTTP ingest → transform → condition → POST or skip branch (`scripts/sample_workflows.py` pipeline).
2. **Scheduled report** — Pull metrics → aggregate with Python → delay window (simulating generation) — wire a schedule via `POST /api/v1/schedules`.
3. **User onboarding** — Create record → welcome notification → delay → follow-up (simulated with HTTP/delay tasks in the sample script).

## Future enhancements

- Visual DAG editor and live validation
- Workflow versioning with rollback and canary releases
- Nested sub-workflows and dynamic fan-out/fan-in
- Dedicated worker pools per task type / tenant
- Workflow marketplace and shared templates

## Tests

```bash
pytest
```

## License

Use and modify freely for interviews, portfolios, and internal prototypes.
