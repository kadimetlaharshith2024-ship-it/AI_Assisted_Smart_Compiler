from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api.routes import router as compile_router

app = FastAPI(title="AI-Assisted Smart Compiler API")

# Allow the frontend (running on a different origin/port during development)
# to call this API from the browser. Tighten allow_origins to your deployed
# frontend URL(s) before shipping this beyond local demos.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(compile_router, prefix="/api")

@app.get("/")
def read_root():
    return {"message": "Smart Compiler Backend is running!"}