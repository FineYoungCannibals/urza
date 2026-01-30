# server.py
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Optional
import uvicorn
from urza.config.display import BANNER, API_WELCOME
from config.settings import is_ready

app = FastAPI(title="Urza API", version="0.1.0")


@app.get("/")
def root():
    return {"message": API_WELCOME}
