"""OpsPilot FastAPI application entry point."""
import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv

load_dotenv()

# Wire LangSmith before importing agent code
os.environ.setdefault("LANGCHAIN_TRACING_V2", "true")
os.environ.setdefault("LANGCHAIN_PROJECT", "opspilot")

from api.webhook import router as webhook_router
from api.telemetry import router as telemetry_router

app = FastAPI(title="OpsPilot", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(webhook_router, prefix="/api")
app.include_router(telemetry_router, prefix="/api")


@app.get("/health")
async def health():
    return {"status": "ok"}
