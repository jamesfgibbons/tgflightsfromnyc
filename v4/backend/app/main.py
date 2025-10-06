from __future__ import annotations
import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .routers.health import router as health_router
from .routers.board import router as board_router
from .routers.travel import router as travel_router
from .routers.llm import router as llm_router


def _cors_origins() -> list[str]:
    raw = os.getenv("CORS_ORIGINS", "")
    return [o.strip() for o in raw.split(",") if o.strip()]


app = FastAPI(title="SERPRadio v4 Backend", version="4.0.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins() or ["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health_router)
app.include_router(board_router)
app.include_router(travel_router)
app.include_router(llm_router)


@app.get("/")
def root():
    return {"ok": True, "name": "serpradio-v4", "version": "4.0.0"}

