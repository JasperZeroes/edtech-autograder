import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.presentation.api.assessment import router as assessment_router
from app.presentation.api.auth import router as auth_router
from app.presentation.api.results import router as results_router
from app.presentation.api.submission import router as submission_router


app = FastAPI(
    title="EdTech Autograder API",
    version="0.1.0",
)

frontend_origin = os.getenv(
    "FRONTEND_ORIGIN",
    "http://localhost:5173",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[frontend_origin],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router)
app.include_router(assessment_router)
app.include_router(submission_router)
app.include_router(results_router)


@app.get("/health", tags=["Health"])
def health_check() -> dict[str, str]:
    return {"status": "ok"}
