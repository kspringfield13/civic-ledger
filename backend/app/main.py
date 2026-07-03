"""civic-ledger API — produces risk signals and review queues, never accusations."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .config import settings
from .routers import cases, entities, health, risk_signals, sources

app = FastAPI(
    title="civic-ledger",
    description=(
        "Lawful fraud/waste/abuse risk-intelligence API. Outputs are leads and "
        "risk signals with confidence scores for human review — not findings."
    ),
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_methods=["GET"],
    allow_headers=["*"],
)

app.include_router(health.router)
app.include_router(sources.router)
app.include_router(entities.router)
app.include_router(risk_signals.router)
app.include_router(cases.router)
