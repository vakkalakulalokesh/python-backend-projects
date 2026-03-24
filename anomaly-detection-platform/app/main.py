import logging
from contextlib import asynccontextmanager
from typing import AsyncIterator

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.routes import anomalies, dashboard, metrics, rules, websocket
from app.cache import init_redis, shutdown_redis
from app.config import settings
from app.kafka_client import KafkaProducerClient
from app.kafka_client.consumer import MetricConsumer
from app.models.database import engine

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

metric_consumer: MetricConsumer | None = None
_kafka_cm: KafkaProducerClient | None = None


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    global metric_consumer, _kafka_cm
    await init_redis()
    app.state.kafka_producer = None
    try:
        _kafka_cm = KafkaProducerClient(settings.KAFKA_BOOTSTRAP_SERVERS)
        await _kafka_cm.__aenter__()
        app.state.kafka_producer = _kafka_cm
    except Exception:
        logger.warning("Kafka producer unavailable; continuing without publish")
    metric_consumer = MetricConsumer()
    try:
        metric_consumer.start()
    except Exception:
        logger.warning("Metric consumer failed to start")
    yield
    if metric_consumer is not None:
        await metric_consumer.stop()
    if _kafka_cm is not None:
        try:
            await _kafka_cm.__aexit__(None, None, None)
        except Exception:
            logger.warning("Kafka producer shutdown error")
        _kafka_cm = None
    await shutdown_redis()
    await engine.dispose()


app = FastAPI(
    title="Anomaly Detection Platform",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(Exception)
async def unhandled_exception_handler(
    request: Request, exc: Exception
) -> JSONResponse:
    logger.exception("unhandled error: %s", exc)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"detail": "internal server error"},
    )


@app.exception_handler(RequestValidationError)
async def validation_handler(
    request: Request, exc: RequestValidationError
) -> JSONResponse:
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={"detail": exc.errors()},
    )


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


app.include_router(metrics.router, prefix="/api/v1")
app.include_router(anomalies.router, prefix="/api/v1")
app.include_router(rules.router, prefix="/api/v1")
app.include_router(dashboard.router, prefix="/api/v1")
app.include_router(websocket.router)
