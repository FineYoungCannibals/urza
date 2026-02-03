# server.py
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Optional
import uvicorn
from urza.config.display import BANNER, APP_WELCOME, APP_DESC, APP_VERSION
from config.settings import is_ready, setup_logging, setup_urza, settings
import logging

setup_logging()

logger = logging.getLogger(__name__)
app = FastAPI(
    title="Urza API",
    description=APP_DESC,
    version="0.1.0"
)

# explicit route declaration 
from routes import bots

app.include_router(bots.router, prefix="/bots", tags=["bots"])

@app.get("/health", tags=["health"])
async def health_check():
    resp_dict = {"status":"healthy", "service":"urza-api"}
    # check db connectivity
    # check tg connectivity
    # check do spaces connectivity
    return resp_dict

@app.get("/")
def root():
    return {
        "message": APP_WELCOME,
        "version": APP_VERSION,
        "docs": "/docs"
    }

if __name__=="__main__":
    import uvicorn
    logger.info(f"Starting Urza API on {settings.api_host}:{settings.api_port}")
    uvicorn.run(
        "app:app",
        host=settings.api_host,
        port=settings.api_port,
        reload=True,
        log_level=settings.log_level.lower()
    )