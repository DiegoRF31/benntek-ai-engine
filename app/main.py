from fastapi import FastAPI

app = FastAPI(
    title="Benntek AI Engine",
    version="0.1.0"
)

@app.get("/")
def health():
    return {"status": "engine running"}