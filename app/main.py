"""
Mash Voice - Main FastAPI Application

Entry point for the voice agent platform.
"""

from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api import agents_router, calls_router, whatsapp_router, websocket_router
from app.config import get_settings
from app.models import HealthCheck, init_database
from app.tools import register_all_tools
from app.utils import get_logger, setup_logging

# Initialize logging
setup_logging()
logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler."""
    logger.info("Starting Mash Voice Platform")
    
    # Initialize database
    try:
        await init_database()
        logger.info("Database initialized")
    except Exception as e:
        logger.warning(f"Database initialization skipped: {e}")
    
    # Register tools
    register_all_tools()
    logger.info("Tools registered")
    
    yield
    
    # Cleanup
    logger.info("Shutting down Mash Voice Platform")
    
    # Close services
    from app.services import get_asr_service, get_tts_service, get_conversation_manager
    
    try:
        await get_asr_service().close_all()
        await get_tts_service().close()
        await get_conversation_manager().close()
    except Exception as e:
        logger.warning(f"Error during cleanup: {e}")


# Create FastAPI app
settings = get_settings()
app = FastAPI(
    title="Mash Voice Platform",
    description="Modular Full-Stack Voice Agent Platform",
    version="0.1.0",
    lifespan=lifespan,
    debug=settings.debug,
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Exception handlers
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Global exception handler."""
    logger.exception("Unhandled exception", error=str(exc), path=request.url.path)
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error"},
    )


# Health check endpoint
@app.get("/health", response_model=HealthCheck, tags=["health"])
async def health_check():
    """Health check endpoint."""
    services = {
        "api": "healthy",
    }
    
    # Check Redis
    try:
        from app.core.state import get_state_manager
        manager = get_state_manager()
        await manager.get_active_calls()
        services["redis"] = "healthy"
    except Exception as e:
        services["redis"] = f"unhealthy: {e}"
    
    # Check database
    try:
        from app.models import get_engine
        engine = get_engine()
        async with engine.connect() as conn:
            await conn.execute("SELECT 1")
        services["database"] = "healthy"
    except Exception as e:
        services["database"] = f"unhealthy: {e}"
    
    return HealthCheck(
        status="healthy" if all("healthy" == v for v in services.values()) else "degraded",
        version="0.1.0",
        services=services,
    )


# Root endpoint
@app.get("/", tags=["root"])
async def root():
    """Root endpoint."""
    return {
        "name": "Mash Voice Platform",
        "version": "0.1.0",
        "docs": "/docs",
        "health": "/health",
    }


# Include routers
app.include_router(whatsapp_router, prefix="/api/v1")
app.include_router(calls_router, prefix="/api/v1")
app.include_router(agents_router, prefix="/api/v1")
app.include_router(websocket_router, prefix="/api/v1")


# Run with uvicorn
if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(
        "app.main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.debug,
    )
