from __future__ import annotations

import asyncio
from contextlib import asynccontextmanager
from typing import Dict

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.routes import dashboard, executions, schedules, tasks, websocket as ws_routes, workflows
from app.api.routes.websocket import redis_listener_loop
from app.config import settings


@asynccontextmanager
async def lifespan(app: FastAPI):
    listener = asyncio.create_task(redis_listener_loop(settings.REDIS_URL))
    try:
        yield
    finally:
        listener.cancel()
        try:
            await listener
        except asyncio.CancelledError:
            pass


app = FastAPI(
    title="Workflow Orchestration Engine",
    version="1.0.0",
    description="Distributed DAG workflows with Celery, PostgreSQL, and Redis.",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(RequestValidationError)
async def validation_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    return JSONResponse(status_code=422, content={"detail": exc.errors()})


@app.get("/health")
async def health() -> Dict[str, str]:
    return {"status": "ok"}


api = "/api/v1"
app.include_router(workflows.router, prefix=api)
app.include_router(executions.router, prefix=api)
app.include_router(tasks.router, prefix=api)
app.include_router(schedules.router, prefix=api)
app.include_router(dashboard.router, prefix=api)
app.include_router(ws_routes.router)
