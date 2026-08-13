"""
main.py - FastAPI application entrypoint.

Thin HTTP wrapper around engine/ - the same analyze() and generate_excel()
app.py (Streamlit) already calls. No business logic lives here; this file's
only job is wiring HTTP requests into calls into engine/ and engine/'s output
back into HTTP responses. Run with:

    uvicorn backend.main:app --reload
"""

import os

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from .routes import analyze, export

app = FastAPI(
    title="Bank Statement Analyser API",
    description="Rule-based bank statement extraction, reconciliation, and underwriting signals.",
    version="0.1.0",
)

# Local dev origins always allowed; the deployed frontend's real origin(s)
# come from an env var (set on Render, e.g. "https://<project>.vercel.app")
# rather than being hardcoded, so a new Vercel domain doesn't need a code
# change + redeploy. Never "*": this API accepts file uploads.
_extra_origins = [o.strip() for o in os.environ.get("ALLOWED_ORIGINS", "").split(",") if o.strip()]
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        *_extra_origins,
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(analyze.router, prefix="/api")
app.include_router(export.router, prefix="/api")


@app.get("/api/health")
def health() -> dict:
    return {"status": "ok"}


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    # A route's own try/except already turns expected failures (locked PDF,
    # unreadable file) into 4xx responses with a specific error_code - this
    # is the backstop for anything that reaches here uncaught, so a client
    # never sees a raw Python traceback.
    return JSONResponse(
        status_code=500,
        content={
            "error_code": "INTERNAL_ERROR",
            "message": "Something went wrong processing this request.",
        },
    )
