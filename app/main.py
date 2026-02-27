from fastapi import FastAPI
from sqlalchemy import text
from app.core.database import engine

# Import routers directly (clean architecture approach)
from app.api.challenges import router as challenges_router
from app.api.submission import router as submission_router
from app.api.auth import router as auth_router
from app.api.analytics import router as analytics_router


app = FastAPI(
    title="Benntek AI Engine",
    version="0.1.0"
)

# Register API routers
app.include_router(challenges_router, prefix="/challenges", tags=["Challenges"])
app.include_router(submission_router)  # prefix already defined in file
app.include_router(auth_router, prefix="/auth", tags=["Auth"])
app.include_router(analytics_router, prefix="/analytics", tags=["Analytics"])


@app.get("/")
def health():
    """
    Health check endpoint.
    Used to verify the API is running.
    """
    return {"status": "engine running"}


@app.get("/db-test")
def db_test():
    """
    Simple database connectivity test.
    """
    with engine.connect() as connection:
        result = connection.execute(text("SELECT 1"))
        return {"db_response": result.scalar()}


@app.get("/tables")
def get_tables():
    """
    Returns all public tables in the database.
    Useful for debugging.
    """
    with engine.connect() as conn:
        result = conn.execute(
            text(
                "SELECT table_name "
                "FROM information_schema.tables "
                "WHERE table_schema='public'"
            )
        )
        return [row[0] for row in result]