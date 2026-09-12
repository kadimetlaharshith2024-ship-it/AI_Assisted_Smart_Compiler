from fastapi import FastAPI
from app.api.routes import router as compile_router

app = FastAPI(title="AI-Assisted Smart Compiler API")

app.include_router(compile_router, prefix="/api")

@app.get("/")
def read_root():
    return {"message": "Smart Compiler Backend is running!"}