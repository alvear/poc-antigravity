from fastapi import FastAPI
from app.routers import auth

app = FastAPI(title="OAuth SSO Service", version="1.0.0")
app.include_router(auth.router, prefix="/v1")

@app.get("/health")
async def health() -> dict:
    """Health check endpoint."""
    return {"status": "ok", "service": "oauth-sso"}
