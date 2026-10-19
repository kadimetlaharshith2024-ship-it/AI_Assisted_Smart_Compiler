import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api.routes import router as compile_router

# The Vite dev server's default addresses. In production set CORS_ORIGINS to your
# deployed frontend URL(s), comma-separated; use "*" only for throwaway demos.
DEFAULT_CORS_ORIGINS = ["http://localhost:5173", "http://127.0.0.1:5173"]


def cors_origins():
    raw = os.environ.get("CORS_ORIGINS", "")
    origins = [o.strip() for o in raw.split(",") if o.strip()]
    return origins or DEFAULT_CORS_ORIGINS


app = FastAPI(title="AI-Assisted Smart Compiler API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins(),
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(compile_router, prefix="/api")

@app.get("/")
def read_root():
    return {"message": "Smart Compiler Backend is running!"}
