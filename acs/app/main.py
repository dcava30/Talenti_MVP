"""
Talenti ACS Service - FastAPI Application
Handles Azure Communication Services call automation and recording
"""
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import logging

from app.config import settings
from app.api.routes import calls, recordings, health
from app.services.supabase_client import supabase_service

# Configure logging
logging.basicConfig(
    level=getattr(logging, settings.LOG_LEVEL),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager"""
    logger.info("Starting Talenti ACS Service...")
    logger.info(f"ACS Endpoint: {settings.ACS_ENDPOINT}")
    yield
    logger.info("Shutting down Talenti ACS Service...")


app = FastAPI(
    title="Talenti ACS Service",
    description="Azure Communication Services integration for AI interviews",
    version="1.0.0",
    lifespan=lifespan
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(health.router, tags=["Health"])
app.include_router(calls.router, prefix="/api/calls", tags=["Calls"])
app.include_router(recordings.router, prefix="/api/recordings", tags=["Recordings"])


@app.get("/")
async def root():
    return {
        "service": "Talenti ACS Service",
        "version": "1.0.0",
        "status": "running"
    }
