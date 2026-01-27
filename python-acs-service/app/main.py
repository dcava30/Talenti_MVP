"""
Talenti ACS Service - FastAPI Application
Handles Azure Communication Services call automation and recording
"""
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import logging

from app.config import settings
from app.api.router import api_router

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
cors_origins = [settings.FRONTEND_ORIGIN] if settings.FRONTEND_ORIGIN else settings.ALLOWED_ORIGINS

app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(api_router)


@app.get("/")
async def root():
    return {
        "service": "Talenti ACS Service",
        "version": "1.0.0",
        "status": "running"
    }
