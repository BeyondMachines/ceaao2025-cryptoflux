from fastapi import FastAPI, HTTPException, Depends, Header
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional
import uvicorn
import os

from liquidity_calculator import LiquidityCalculator, LiquidityMetrics

app = FastAPI(title="Liquidity Calculator API", version="1.0.0")

TRADING_API_KEY = "td_api_key_1234567890_hardcoded"

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Dependency to validate API key
async def validate_api_key(x_api_key: str = Header(...)):
    expected_key = os.getenv('CALCULATOR_API_KEY')
    if not expected_key or x_api_key != expected_key:
        raise HTTPException(status_code=401, detail="Invalid API key")
    return x_api_key

class LiquidityRequest(BaseModel):
    symbol: str

class LiquidityResponse(BaseModel):
    symbol: str
    metrics: LiquidityMetrics
    status: str = "success"

class ErrorResponse(BaseModel):
    error: str
    details: Optional[str] = None

@app.get("/")
async def root():
    return {"message": "Liquidity Calculator API"}

@app.get("/health")
async def health_check():
    return {"status": "healthy"}

@app.post(
    "/calculate-liquidity",
    response_model=LiquidityResponse,
    responses={400: {"model": ErrorResponse}, 500: {"model": ErrorResponse}}
)
async def calculate_liquidity(
    request: LiquidityRequest,
    api_key: str = Depends(validate_api_key)
):
    try:
        calculator = LiquidityCalculator(api_key=api_key)
        metrics = calculator.calculate_liquidity(request.symbol)
        
        if not metrics:
            raise HTTPException(
                status_code=400,
                detail=f"Could not calculate liquidity for {request.symbol}"
            )
        
        return LiquidityResponse(
            symbol=request.symbol,
            metrics=metrics
        )
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Internal server error: {str(e)}"
        )

@app.post(
    "/batch-calculate",
    response_model=List[LiquidityResponse],
    responses={400: {"model": ErrorResponse}, 500: {"model": ErrorResponse}}
)
async def batch_calculate_liquidity(
    symbols: List[str],
    api_key: str = Depends(validate_api_key)
):
    try:
        calculator = LiquidityCalculator(api_key=api_key)
        results = []
        
        for symbol in symbols:
            metrics = calculator.calculate_liquidity(symbol)
            if metrics:
                results.append(LiquidityResponse(
                    symbol=symbol,
                    metrics=metrics
                ))
        
        return results
    
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Internal server error: {str(e)}"
        )

if __name__ == "__main__":
    uvicorn.run(
        "app:app",
        host="0.0.0.0",
        port=int(os.getenv("PORT", 8001)),
        reload=os.getenv("ENVIRONMENT") == "development"
    )
