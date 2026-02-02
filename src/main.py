from contextlib import asynccontextmanager
from fastapi import FastAPI

from src.database.connection import init_database

@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_database()
    yield

app = FastAPI(
    title="Amnezia API",
    version="1.0.0",
    lifespan=lifespan,
    root_path="/api/v1",
)

@app.get("/health")
async def health_check():
    return {
        "app": "Amnezia API",
        "status": "running"
    }