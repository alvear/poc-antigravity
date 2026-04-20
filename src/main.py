from fastapi import FastAPI
import os

app = FastAPI(
    title="POC Antigravity - OAuth Service",
    version="0.1.0",
    description="Bootstrap service - substituido pelo merge do PR #1"
)


@app.get("/health")
async def health() -> dict:
    """Liveness probe."""
    return {
        "status": "ok",
        "service": "poc-antigravity",
        "env": os.getenv("ENV", "unknown"),
        "version": os.getenv("VERSION", "0.1.0"),
    }


@app.get("/")
async def root() -> dict:
    """Hello world endpoint para validar o deploy."""
    return {
        "message": "POC Antigravity - pipeline agentico funcionando",
        "env": os.getenv("ENV", "unknown"),
    }
