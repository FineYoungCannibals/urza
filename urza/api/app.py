# urza/api/app.py
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Optional
import uvicorn
from urza.config.display import BANNER, APP_WELCOME, APP_DESC, APP_VERSION
from urza.config.settings import setup_logging, settings
from urza.config.startup import check_setup, setup_urza
from contextlib import asynccontextmanager

# Routes
from urza.api.routes import users
from urza.api.routes import api_keys
from urza.api.routes import tasks

import logging

logger = logging.getLogger(__name__)
app = FastAPI(
    title="Urza API",
    description=APP_DESC,
    version="0.1.0"
)

app.include_router(users.router)
app.include_router(api_keys.router)
app.include_router(tasks.router)

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger = setup_logging()
    logger.info(f"Starting Urza API on {settings.api_host}:{settings.api_port}")
    # Does the session file exist?
    if not check_setup():
        setup_urza()
    # Is Telegram Connected? 
    
    # Can we connect to DO?
    
    # Check we can connect to the database

    # Yield for the app
    yield

    # Shutting down the app
    logger.info("Shutting down Urza")



@app.get("/health", tags=["health"])
async def health_check():
    resp_dict = {"status":"healthy", "service":"urza-api"}
    # check db connectivity
    # check tg authentication status
    # check tg channel connectivity
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
    uvicorn.run(
        "app:app",
        host=settings.api_host,
        port=settings.api_port,
        reload=True,
        log_level=settings.log_level.lower()
    )