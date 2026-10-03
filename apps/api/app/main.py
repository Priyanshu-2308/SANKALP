"""FastAPI main application entrypoint for SANKALP Travel Recovery API."""

from contextlib import asynccontextmanager
from typing import AsyncGenerator
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .config import settings
from .dependencies import get_data_source, get_database
from .routers import v1_confirm, v1_places, v1_search, v1_simulate


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Startup and shutdown lifecycle handler."""
    # Ensure database tables and indices exist
    db = get_database()
    db.init_db()

    # Pre-warm singleton transport data source cache
    get_data_source()

    yield


app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    description=(
        "Autonomous multi-modal journey-recovery platform for India. "
        "Provides probabilistic recovery itineraries with Monte Carlo delay simulation, "
        "Pareto multi-objective ranking, and single-use human approval tokens."
    ),
    lifespan=lifespan,
)

# Configure Cross-Origin Resource Sharing (CORS)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register versioned API routers
app.include_router(v1_places.router)
app.include_router(v1_search.router)
app.include_router(v1_confirm.router)
app.include_router(v1_simulate.router)


@app.get("/", tags=["System"])
def root_status() -> dict[str, str]:
    """Root status endpoint with project metadata and data disclaimer."""
    return {
        "project": settings.PROJECT_NAME,
        "version": settings.VERSION,
        "status": "operational",
        "docs_url": "/docs",
        "data_disclaimer": "Simulated schedules based on static network data. Not connected to live booking systems.",
    }


@app.get("/health", tags=["System"])
def health_check() -> dict[str, str]:
    """Liveness and health verification check."""
    return {"status": "healthy"}
