from fastapi import FastAPI, Depends, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import text

# Import routers directly (clean architecture approach)
from app.api.challenges import router as challenges_router
from app.api.submission import router as submission_router
from app.api.auth import router as auth_router
from app.api.analytics import router as analytics_router
from app.api.admin import router as admin_router
from app.api import instructor
from app.api import dashboard
from app.api.leaderboard import router as leaderboard_router
from app.api.learning import router as learning_router
from app.api.ai_router import router as ai_router
from app.api.cohorts import router as cohorts_router
from app.api.reports import router as reports_router
from app.api.coaching import router as coaching_router
from app.api.ai_players import router as ai_players_router


from app.core.database import Base, engine
from app.infrastructure.models.user_model import User
from app.api.auth import get_current_user


app = FastAPI(
    title="Benntek AI Engine",
    version="0.1.0"
)

origins = [
    "http://localhost:5173",
    "http://127.0.0.1:5173",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    """Ensure CORS headers are present on unhandled 500 errors."""
    origin = request.headers.get("origin", "")
    headers = {}
    if origin in origins:
        headers["Access-Control-Allow-Origin"] = origin
        headers["Access-Control-Allow-Credentials"] = "true"
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error"},
        headers=headers,
    )


#Base.metadata.create_all(bind=engine)

# Register API routers
app.include_router(challenges_router, prefix="/challenges")
app.include_router(submission_router)
app.include_router(auth_router, prefix="/auth")
app.include_router(analytics_router, prefix="/analytics")
app.include_router(instructor.router)
app.include_router(admin_router)
app.include_router(dashboard.router)
app.include_router(leaderboard_router)
app.include_router(learning_router)
app.include_router(ai_router)
app.include_router(cohorts_router)
app.include_router(reports_router)
app.include_router(coaching_router)
app.include_router(ai_players_router)

@app.get("/")
def health():
    return {"status": "engine running"}


@app.get("/db-test")
def db_test():
    """
    Simple database connectivity test.
    """
    with engine.connect() as connection:
        result = connection.execute(text("SELECT 1"))
        return {"db_response": result.scalar()}

    
@app.get("/me")
def read_me(current_user: User = Depends(get_current_user)):
    return {
        "id": current_user.id,
        "email": current_user.email,
        "role": current_user.role
    }