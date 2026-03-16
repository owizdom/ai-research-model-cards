from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from src.core.config import settings
from packages.db.session import init_db


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    yield


app = FastAPI(
    title="AI Policy Intelligence API",
    description="REST API for AI safety policy research platform",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

from src.api.v1 import documents, labs, intersection, probes, responses, slant  # noqa

app.include_router(documents.router, prefix="/api/v1/documents", tags=["Documents"])
app.include_router(labs.router, prefix="/api/v1/labs", tags=["Labs"])
app.include_router(intersection.router, prefix="/api/v1/analysis/intersection", tags=["Intersection"])
app.include_router(probes.router, prefix="/api/v1/probes", tags=["Probes"])
app.include_router(responses.router, prefix="/api/v1/responses", tags=["Responses"])
app.include_router(slant.router, prefix="/api/v1/analysis/slant", tags=["Slant"])


@app.get("/health", tags=["Meta"])
async def health():
    return {"status": "ok", "version": "1.0.0"}
