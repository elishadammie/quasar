# app/main.py (CORS Middleware)

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from typing import Dict

# Import the chat router we created
from app.api.v1 import chat

app = FastAPI(
    title="Quasar",
    description="An Agentic, Adaptive RAG Platform for Enterprise Knowledge.",
    version="0.1.0"
)

# --- Add CORS Middleware ---
# This is the new section that fixes the error.
# It allows your browser-based UI to communicate with the backend API.
origins = [
    # For local development, allowing all origins is often easiest.
    # In a real production environment, you would restrict this to your actual frontend's domain.
    "*" 
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"], # Allow all methods, including POST and OPTIONS
    allow_headers=["*"], # Allow all headers
)
# --- End of CORS Middleware section ---


@app.get("/", tags=["Health Check"])
async def read_root() -> Dict[str, str]:
    """A simple health check endpoint."""
    return {"status": "ok", "message": "Welcome to the Quasar API!"}

# Include the API router.
app.include_router(chat.router, prefix="/api/v1")