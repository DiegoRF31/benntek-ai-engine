from fastapi import FastAPI
from sqlalchemy import text
from app.core.database import engine

app = FastAPI(
    title="Benntek AI Engine",
    version="0.1.0"
)

@app.get("/")
def health():
    return {"status": "engine running"}

@app.get("/db-test")
def db_test():
    with engine.connect() as connection:
        result = connection.execute(text("SELECT 1"))
        return {"db_response": result.scalar()}

@app.get("/tables")
def get_tables():
    with engine.connect() as conn:
        result = conn.execute(
            text("SELECT table_name FROM information_schema.tables WHERE table_schema='public'")
        )
        return [row[0] for row in result]