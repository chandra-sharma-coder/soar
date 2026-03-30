from fastapi import FastAPI
from app.routes import router

app = FastAPI(
    title="Urlscan SOAR SDK App",
    description="Modern SDK-style connector using FastAPI",
    version="1.0.0"
)

app.include_router(router)