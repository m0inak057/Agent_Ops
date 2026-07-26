"""Database engine and session management for the AgentOps backend.

Provides the async SQLAlchemy engine, session factory, and a FastAPI
dependency for obtaining a database session per request.
"""


def get_engine():
    """Create and return the async SQLAlchemy engine."""
    pass


def get_session_factory():
    """Create and return the async session factory bound to the engine."""
    pass


async def get_db():
    """FastAPI dependency that yields a database session."""
    pass
