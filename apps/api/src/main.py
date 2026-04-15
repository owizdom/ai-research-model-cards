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
    title="Model Card Explorer API",
    description="REST API for AI model card governance research platform",
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

from src.api.v1 import documents, labs, intersection, evals, families, deploy, export  # noqa

app.include_router(documents.router, prefix="/api/v1/documents", tags=["Documents"])
app.include_router(labs.router, prefix="/api/v1/labs", tags=["Labs"])
app.include_router(intersection.router, prefix="/api/v1/analysis/intersection", tags=["Intersection"])
app.include_router(evals.router, prefix="/api/v1/evals", tags=["Evals"])
app.include_router(families.router, prefix="/api/v1/families", tags=["Model Families"])
app.include_router(deploy.router, prefix="/api/v1/deploy", tags=["Deploy"])
app.include_router(export.router, prefix="/api/v1/export", tags=["Export"])


@app.get("/health", tags=["Meta"])
async def health():
    return {"status": "ok", "version": "1.0.0"}
