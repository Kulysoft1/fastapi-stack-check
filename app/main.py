# app/main.py
import logging
import os
import uuid
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from app.config import get_settings
from app.db import close_db, init_db
from app.redis_client import close_redis, init_redis
from app.routers import health, kv, notes

settings = get_settings()

# Configure structured logging
logging.basicConfig(
    level=logging.INFO if settings.ENVIRONMENT == "prod" else logging.DEBUG,
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager."""
    # Startup
    logger.info("Starting application...")
    db_ok = False
    redis_ok = False
    
    try:
        await init_db()
        db_ok = True
        logger.info("Database connected")
    except Exception as e:
        logger.warning(f"Database connection failed: {e}. Notes endpoints will return 503.")
    
    try:
        await init_redis()
        redis_ok = True
        logger.info("Redis connected")
    except Exception as e:
        logger.warning(f"Redis connection failed: {e}. KV endpoints will return 503.")
    
    if not db_ok and not redis_ok:
        logger.error("Both database and Redis unavailable!")
    
    logger.info("Application started")

    yield

    # Shutdown
    logger.info("Shutting down application...")
    await close_redis()
    await close_db()
    logger.info("Application shutdown complete")


app = FastAPI(
    title="FastAPI Stack Check",
    description="Minimal FastAPI app with PostgreSQL and Redis for Render/Railway deployment",
    version="0.1.0",
    lifespan=lifespan,
)

# CORS - allow all for local/deploy testing
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Request ID middleware
@app.middleware("http")
async def add_request_id(request: Request, call_next):
    request_id = request.headers.get("X-Request-ID", str(uuid.uuid4())[:8])
    request.state.request_id = request_id

    # Add request ID to logging context
    logger.info(f"rid={request_id} method={request.method} path={request.url.path}")

    response = await call_next(request)
    response.headers["X-Request-ID"] = request_id
    return response


# Exception handlers for store unavailability
@app.exception_handler(ConnectionError)
async def connection_error_handler(request: Request, exc: ConnectionError):
    logger.error(f"rid={request.state.request_id} connection_error: {exc}")
    return Response(
        content='{"detail": "Service temporarily unavailable"}',
        status_code=503,
        media_type="application/json",
    )


# Templates and static files (absolute paths so they resolve regardless of
# the working directory the process is launched from)
_BASE = os.path.dirname(os.path.abspath(__file__))
templates = Jinja2Templates(directory=os.path.join(_BASE, "templates"))
app.mount("/static", StaticFiles(directory=os.path.join(_BASE, "static")), name="static")


# Index page
@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    return templates.TemplateResponse(request, "index.html")


# Include routers
app.include_router(health.router)
app.include_router(notes.router)
app.include_router(kv.router)