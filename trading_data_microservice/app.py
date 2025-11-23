# app.py (trading_data microservice)
from fastapi import FastAPI
from fastapi.responses import Response
from src.routers.liquidity import router as liq_router

app = FastAPI(title="Trading/Liquidity Microservice")
app.include_router(liq_router, prefix="/api/v1")

@app.get("/health")
def health():
    return {"status": "ok"}

# nice root so / doesn’t 404
@app.get("/", include_in_schema=False)
def root():
    return {
        "service": "trading_data",
        "status": "ok",
        "docs": "/docs",
        "health": "/health",
        "api": "/api/v1"
    }

# silence the favicon request
@app.get("/favicon.ico", include_in_schema=False)
def favicon():
    return Response(status_code=204)

@app.get("/internal/info")
def internal_info():
    import os
    return {
        "db_user": os.getenv("DB_USER"),
        "db_name": os.getenv("DB_NAME"),
        "warning": "this internal endpoint should not be exposed!"
    }