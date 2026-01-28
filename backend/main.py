import os
from fastapi import FastAPI
import logging
import sys

# Configure logging to show up in Docker/Console logs
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)]
)
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from backend.api.router import router

app = FastAPI(title="DeepSeek OCR Platform")

# CORS Setup
origins = ["*"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Create necessary directories at startup
@app.on_event("startup")
async def startup_event():
    os.makedirs("data/uploads", exist_ok=True)
    os.makedirs("data/processed", exist_ok=True)
    from backend import database
    database.init_db()

# Include API Router
app.include_router(router, prefix="/api")

# Serve frontend static files (will be populated after frontend build)
# app.mount("/", StaticFiles(directory="frontend/dist", html=True), name="static")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("backend.main:app", host="0.0.0.0", port=8000, reload=True)
