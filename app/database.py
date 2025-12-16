"""
Database Session Management - Core database connectivity layer
"""

from sqlalchemy import create_engine, event
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from typing import Generator
import logging

from app.core.config import settings

logger = logging.getLogger(__name__)

# Create database engine with connection pooling
engine = create_engine(
    settings.DATABASE_URL,  # PostgreSQL connection string from environment
    pool_size=settings.DB_POOL_SIZE,  # Number of persistent connections
    max_overflow=settings.DB_MAX_OVERFLOW,  # Additional connections when pool is exhausted
    pool_timeout=settings.DB_POOL_TIMEOUT,  # Wait time for available connection
    pool_pre_ping=True,  # Verify connection health before using (prevents stale connections)
    echo=settings.DEBUG,  # Log all SQL queries in debug mode
)

# Log when new database connections are established (debugging aid)
@event.listens_for(engine, "connect")
def receive_connect(dbapi_conn, connection_record):
    logger.debug("🔌 New database connection established")

# Log when connections are closed (track connection lifecycle)
@event.listens_for(engine, "close")
def receive_close(dbapi_conn, connection_record):
    logger.debug("🔌 Database connection closed")

# Session factory - creates new sessions for each request
SessionLocal = sessionmaker(
    autocommit=False,  # Require explicit commits (safer, prevents accidental data changes)
    autoflush=False,   # Control when changes are flushed to database
    bind=engine,       # Bind sessions to our configured engine
)

# Base class for all SQLAlchemy models - provides metadata and table registry
Base = declarative_base()

def get_db() -> Generator[Session, None, None]:
    """
    FastAPI dependency that provides database session per request.
    Automatically handles session lifecycle and cleanup.
    """
    db = SessionLocal()  # Create new session for this request
    try:
        yield db  # Provide session to endpoint
    except Exception as e:
        logger.error(f"❌ Database error during request: {str(e)}", exc_info=True)  # Log full stack trace
        db.rollback()  # Rollback failed transaction to prevent partial commits
        raise  # Re-raise exception to FastAPI for proper HTTP error response
    finally:
        db.close()  # Always close session (prevents connection leaks)
        logger.debug("✅ Database session closed")

def init_db() -> None:
    """
    Initialize database by creating all tables.
    Used for development setup - production should use Alembic migrations.
    """
    logger.info("🏗️  Creating database tables...")
    try:
        from app.models import user, task, audit_log  # Import models to register with Base
        Base.metadata.create_all(bind=engine)  # Create all tables defined in models
        logger.info("✅ Database tables created successfully")
    except Exception as e:
        logger.error(f"❌ Failed to create database tables: {str(e)}", exc_info=True)
        raise  # Fail fast - app shouldn't start without database

def check_db_connection() -> bool:
    """
    Verify database connectivity - used for health checks and startup validation.
    Returns True if connection successful, False otherwise.
    """
    try:
        db = SessionLocal()  # Attempt to create session
        db.execute("SELECT 1")  # Execute simple query to verify connectivity
        db.close()  # Clean up test session
        logger.info("✅ Database connection successful")
        return True
    except Exception as e:
        logger.error(f"❌ Database connection failed: {str(e)}", exc_info=True)
        return False

def get_pool_stats() -> dict:
    """
    Get current database connection pool statistics.
    Useful for monitoring connection usage and detecting leaks.
    """
    pool = engine.pool  # Access connection pool
    return {
        "pool_size": pool.size(),  # Total connections in pool
        "checked_out": pool.checkedout(),  # Currently active connections
        "overflow": pool.overflow(),  # Connections beyond pool_size
        "checked_in": pool.checkedin(),  # Idle connections in pool
    }

def close_db_connections():
    """
    Gracefully close all database connections.
    Called during application shutdown to prevent "too many connections" errors.
    """
    logger.info("🔌 Closing database connections...")
    engine.dispose()  # Close all connections in pool
    logger.info("✅ All database connections closed")