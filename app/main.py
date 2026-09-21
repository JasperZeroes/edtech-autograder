from fastapi import FastAPI

from app.presentation.api.auth import router as auth_router


app = FastAPI(
    title="EdTech Autograder API",
    version="0.1.0",
)

app.include_router(auth_router)


@app.get("/health", tags=["Health"])
def health_check() -> dict[str, str]:
    return {"status": "ok"}
