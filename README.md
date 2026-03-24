# Python Backend Projects

A collection of production-grade Python backend projects demonstrating advanced async programming, event-driven architecture, distributed systems, and ML-powered analytics.

## Projects

### 1. [Real-Time Anomaly Detection Platform](./anomaly-detection-platform)
A production-grade observability platform that ingests application and infrastructure metrics, detects anomalies in real-time using 6 statistical and ML algorithms, and provides instant alerting.

**Architecture:** FastAPI + Kafka + Redis + Celery + PostgreSQL

**Tech Stack:** Python 3.11, FastAPI, SQLAlchemy 2.0 (async), Apache Kafka (aiokafka), Redis, Celery, NumPy, SciPy, scikit-learn, WebSocket, Docker

**Key Highlights:**
- 6 anomaly detection algorithms: Z-Score, IQR, MAD, EWMA, Isolation Forest (ML), Seasonal Decomposition
- Kafka-driven metric ingestion pipeline with async consumers
- Redis sliding windows for real-time time-series analysis
- Configurable alert rules with cooldown mechanism to prevent alert storms
- Real-time anomaly alerts via WebSocket
- Celery workers for background batch analysis and data retention cleanup
- RESTful API with full CRUD for sources, rules, anomalies, and dashboard
- Comprehensive test suite for all detection algorithms

---

### 2. [Distributed Workflow Orchestration Engine](./workflow-orchestration-engine)
A production-grade workflow orchestration engine inspired by Temporal and Apache Airflow, providing DAG-based workflow definition, distributed execution with retry strategies, cron scheduling, and real-time monitoring.

**Architecture:** FastAPI + Celery + Redis + PostgreSQL + NetworkX

**Tech Stack:** Python 3.11, FastAPI, SQLAlchemy 2.0 (async), Celery, Redis, NetworkX (DAG engine), croniter, WebSocket, Docker

**Key Highlights:**
- DAG-based workflow definition with cycle detection (NetworkX)
- 5 built-in task types: HTTP Request, Python Expression, Delay/Timer, Condition/Branch, Data Transform
- 3 retry strategies: Fixed, Exponential Backoff (with jitter), Linear
- Execution state machine with strict transition validation
- Cron scheduling with distributed lock coordination (Redis)
- Real-time execution monitoring via WebSocket
- Celery workers for distributed task execution
- Comprehensive test suite for DAG validation, state machine, and retry logic

---

## Architecture & Design Patterns

| Pattern | Project |
|---------|---------|
| Event-Driven Architecture (Kafka) | Anomaly Detection |
| Strategy Pattern (Detectors/Retry) | Both Projects |
| DAG-based Orchestration | Workflow Engine |
| State Machine | Workflow Engine |
| Sliding Window Algorithm | Anomaly Detection |
| Distributed Locking (Redis) | Both Projects |
| Background Workers (Celery) | Both Projects |
| Async/Await Throughout | Both Projects |
| Repository Pattern | Both Projects |

## Quick Start

Each project includes Docker Compose for one-command setup:

```bash
# Anomaly Detection Platform
cd anomaly-detection-platform && docker compose up --build
# API: http://localhost:8000/docs

# Workflow Orchestration Engine
cd workflow-orchestration-engine && docker compose up --build
# API: http://localhost:8000/docs
```

## Author
**Vakkalakula Lokesh** | [lokeshvakkalakula619@gmail.com](mailto:lokeshvakkalakula619@gmail.com)
