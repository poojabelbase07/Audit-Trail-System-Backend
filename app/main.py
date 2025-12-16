"""
FastAPI Application Entry Point - Application initialization and configuration
"""

from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from sqlalchemy.exc import SQLAlchemyError
import logging
import sys
import time

from app.core.config import settings, validate_config, is_production
from app.database import check_db_connection, close_db_connections, get_pool_stats

# Configure application logging with timestamp and log level
logging.basicConfig(
    level=logging.DEBUG if settings.DEBUG else logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger(__name__)

def create_application() -> FastAPI:
    """
    Factory function to create and configure FastAPI application.
    Using factory pattern allows easier testing with different configurations.
    """
    app = FastAPI(
        title=settings.APP_NAME,  # API documentation title
        version=settings.APP_VERSION,  # API version
        debug=settings.DEBUG,  # Enable debug mode in development
        docs_url="/api/docs" if not is_production() else None,  # Hide Swagger docs in production
        redoc_url="/api/redoc" if not is_production() else None,  # Hide ReDoc in production
        description="Production-grade audit trail management system"
    )
    
    setup_middleware(app)  # Configure CORS and request logging
    setup_exception_handlers(app)  # Configure global error handling
    setup_event_handlers(app)  # Configure startup/shutdown hooks
    setup_routers(app)  # Mount API route handlers
    
    return app

def setup_middleware(app: FastAPI) -> None:
    """Configure application middleware - runs on every request/response"""
    
    # CORS middleware - allows frontend to call API from different origin
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.CORS_ORIGINS,  # Allowed domains (e.g., http://localhost:5173)
        allow_credentials=True,  # Allow cookies and auth headers
        allow_methods=["*"],  # Allow all HTTP methods (GET, POST, PUT, DELETE, etc.)
        allow_headers=["*"],  # Allow all request headers
    )
    
    # Request timing and logging middleware
    @app.middleware("http")
    async def log_requests(request: Request, call_next):
        """Log every request with method, path, status, and processing time"""
        start_time = time.time()  # Record request start time
        logger.info(f"➡️  {request.method} {request.url.path}")  # Log incoming request
        
        response = await call_next(request)  # Process request through handlers
        
        process_time = time.time() - start_time  # Calculate total processing time
        logger.info(
            f"⬅️  {request.method} {request.url.path} "
            f"- Status: {response.status_code} - Time: {process_time:.2f}s"
        )
        response.headers["X-Process-Time"] = str(process_time)  # Add timing header for debugging
        return response

def setup_exception_handlers(app: FastAPI) -> None:
    """Configure global exception handlers for consistent error responses"""
    
    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(request: Request, exc: RequestValidationError):
        """
        Handle Pydantic validation errors (invalid request data).
        Returns field-level error details for better debugging.
        """
        errors = []
        for error in exc.errors():  # Extract all validation errors
            errors.append({
                "field": ".".join(str(x) for x in error["loc"]),  # Field path (e.g., "body.email")
                "message": error["msg"],  # Human-readable error message
                "type": error["type"]  # Error type (e.g., "value_error.email")
            })
        
        logger.warning(f"❌ Validation error on {request.url.path}: {errors}")
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content={"error": "Validation Error", "detail": errors, "timestamp": time.time()}
        )
    
    @app.exception_handler(SQLAlchemyError)
    async def database_exception_handler(request: Request, exc: SQLAlchemyError):
        """
        Handle database errors - logs full details but returns generic message.
        Security: Never expose database schema or internal errors to client.
        """
        logger.error(
            f"❌ Database error on {request.method} {request.url.path}: {str(exc)}",
            exc_info=True  # Include full stack trace in logs
        )
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "error": "Database Error",
                "detail": "An error occurred while processing your request. Please try again later.",
                "timestamp": time.time()
            }
        )
    
    @app.exception_handler(Exception)
    async def general_exception_handler(request: Request, exc: Exception):
        """
        Catch-all handler for unexpected exceptions.
        Prevents app crashes and logs full error details for debugging.
        """
        logger.error(
            f"❌ Unhandled exception on {request.method} {request.url.path}: {str(exc)}",
            exc_info=True  # Full stack trace in logs
        )
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "error": "Internal Server Error",
                "detail": "An unexpected error occurred. Our team has been notified.",
                "timestamp": time.time()
            }
        )

def setup_event_handlers(app: FastAPI) -> None:
    """Configure startup and shutdown event handlers"""
    
    @app.on_event("startup")
    async def startup_event():
        """
        Run on application startup - validate config and check dependencies.
        Fail fast: If checks fail, application won't start.
        """
        logger.info("🚀 Starting Audit Trail System...")
        
        try:
            validate_config()  # Validate environment variables and settings
        except Exception as e:
            logger.error(f"❌ Configuration validation failed: {e}")
            sys.exit(1)  # Exit immediately if config is invalid
        
        if not check_db_connection():  # Verify database connectivity
            logger.error("❌ Cannot connect to database. Exiting.")
            sys.exit(1)  # Exit if database unreachable
        
        pool_stats = get_pool_stats()  # Log connection pool statistics
        logger.info(f"📊 Database pool: {pool_stats}")
        logger.info("✅ Application started successfully")
        logger.info(f"🌍 Environment: {settings.ENVIRONMENT}")
        logger.info(f"🔧 Debug mode: {settings.DEBUG}")
    
    @app.on_event("shutdown")
    async def shutdown_event():
        """Run on application shutdown - clean up resources gracefully"""
        logger.info("🛑 Shutting down Audit Trail System...")
        close_db_connections()  # Close all database connections
        logger.info("✅ Shutdown complete")

def setup_routers(app: FastAPI) -> None:
    """Mount API routers - will be implemented in next steps"""
    
    @app.get("/health", tags=["Health"])
    async def health_check():
        """
        Health check endpoint for monitoring and load balancers.
        Returns application status, database connectivity, and version info.
        """
        db_healthy = check_db_connection()  # Check if database is accessible
        pool_stats = get_pool_stats()  # Get connection pool metrics
        
        return {
            "status": "healthy" if db_healthy else "unhealthy",
            "database": "connected" if db_healthy else "disconnected",
            "pool_stats": pool_stats,
            "timestamp": time.time(),
            "version": settings.APP_VERSION
        }
    
    # Include API routers
    from app.api import auth, tasks, audit, users
    app.include_router(auth.router, prefix="/api/auth", tags=["Authentication"])
    app.include_router(tasks.router, prefix="/api/tasks", tags=["Tasks"])
    app.include_router(audit.router, prefix="/api/audit", tags=["Audit Logs"])
    app.include_router(users.router, prefix="/api/users", tags=["Users"])

# Create application instance
app = create_application()

if __name__ == "__main__":
    """
    Direct execution entry point - for development only.
    Production: Use `uvicorn app.main:app --host 0.0.0.0 --port 8000`
    """
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",  # Listen on all network interfaces
        port=8000,  # Default HTTP port
        reload=settings.DEBUG,  # Auto-reload on code changes (development only)
        log_level="debug" if settings.DEBUG else "info"
    )