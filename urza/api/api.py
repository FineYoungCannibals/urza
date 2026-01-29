# server.py
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Optional
import uvicorn
from config.display import BANNER
from config.settings import is_ready

app = FastAPI(title="Urza API", version="0.1.0")

if __name__ == "__main__":
    # For testing directly
    #TODO
    print('todo')