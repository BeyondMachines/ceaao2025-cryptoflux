import os
import requests
import pandas as pd
from typing import Dict, List, Optional
from dataclasses import dataclass
import logging
from datetime import datetime

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class LiquidityMetrics:
    bid_ask_spread: float
    order_book_depth: float
    volume_24h: float
    volatility: float
    liquidity_score: float
    timestamp: str

class LiquidityCalculator:
    def __init__(self, api_key: str, trading_data_url: str = None):
        """
        api_key: The key to authenticate with Trading/Liquidity Microservice
        trading_data_url: Base URL of the Trading/Liquidity Microservice
        """
        self.api_key = api_key
        self.base_url = trading_data_url or os.getenv('TRADING_DATA_URL', 'http://localhost:7100')
        self.session = requests.Session()
        self.session.headers.update({
            'X-API-Key': self.api_key,
            'Content-Type': 'application/json'
        })
    
    def fetch_liquidity_input(self, window_min: int = 15, limit_symbols: int = 6) -> Optional[List[Dict]]:
        """
        Fetch aggregated transaction data from Trading/Liquidity Microservice
        This replaces the direct call to External Trading API
        """
        try:
            url = f"{self.base_url}/api/v1/liquidity/input"
            params = {
                'window_min': window_min,
                'limit_symbols': limit_symbols
            }
            
            response = self.session.get(url, params=params, timeout=30)
            response.raise_for_status()
            data = response.json()
            
            logger.info(f"Fetched liquidity input: {data}")
            
            # Return the items list
            if isinstance(data, dict) and 'items' in data:
                return data['items']
            
            logger.warning(f"Unexpected response format: {data}")
            return []
                
        except Exception as e:
            logger.error(f"Error fetching liquidity input: {e}")
            return None
    
    def calculate_metrics_from_aggregated_data(self, agg_data: Dict) -> Optional[LiquidityMetrics]:
        """
        Calculate liquidity metrics from aggregated transaction data
        
        agg_data format:
        {
            "symbol": "BTC-USD",
            "trades_count": 150,
            "volume_usd": "1234567.89"
        }
        """
        try:
            symbol = agg_data.get('symbol')
            trades_count = int(agg_data.get('trades_count', 0))
            volume_usd = float(agg_data.get('volume_usd', 0))
            
            if trades_count == 0 or volume_usd == 0:
                logger.warning(f"Insufficient data for {symbol}")
                return None
            
            # Estimate metrics based on aggregated data
            
            # 1. Bid-Ask Spread Estimate
            # More trades = tighter spread (better liquidity)
            # Formula: inverse relationship with trade frequency
            spread_estimate = max(0.01, min(5.0, 100 / trades_count))
            
            # 2. Order Book Depth
            # Proxy: volume per trade (higher = deeper book)
            avg_trade_size = volume_usd / trades_count if trades_count > 0 else 0
            order_book_depth = avg_trade_size * 10  # Multiplier for depth estimate
            
            # 3. Volume (already provided)
            volume_24h = volume_usd
            
            # 4. Volatility Estimate
            # More trades with same volume = more volatile (smaller trades)
            # Less trades with high volume = less volatile (institutional)
            volatility = max(1.0, min(50.0, (trades_count / (volume_usd / 10000)) * 5))
            
            metrics_dict = {
                'bid_ask_spread': spread_estimate,
                'order_book_depth': order_book_depth,
                'volume_24h': volume_24h,
                'volatility': volatility
            }
            
            liquidity_score = self.calculate_liquidity_score(metrics_dict)
            
            return LiquidityMetrics(
                bid_ask_spread=spread_estimate,
                order_book_depth=order_book_depth,
                volume_24h=volume_24h,
                volatility=volatility,
                liquidity_score=liquidity_score,
                timestamp=datetime.utcnow().isoformat()
            )
            
        except Exception as e:
            logger.error(f"Error calculating metrics for {agg_data.get('symbol')}: {e}")
            return None
    
    def calculate_liquidity_score(self, metrics: Dict) -> float:
        """Calculate overall liquidity score (0-100)"""
        # Normalize metrics and weight them
        spread_score = max(0, 100 - metrics['bid_ask_spread'] * 10)  # Lower spread = better
        depth_score = min(100, metrics['order_book_depth'] / 1000)   # Higher depth = better
        volume_score = min(100, metrics['volume_24h'] / 1000000)     # Higher volume = better
        volatility_penalty = max(0, 100 - metrics['volatility'] * 2) # Lower volatility = better
        
        # Weighted average
        weights = {'spread': 0.3, 'depth': 0.3, 'volume': 0.3, 'volatility': 0.1}
        total_score = (
            spread_score * weights['spread'] +
            depth_score * weights['depth'] +
            volume_score * weights['volume'] +
            volatility_penalty * weights['volatility']
        )
        
        return min(100, max(0, total_score))
    
    def calculate_liquidity(self, symbol: str = None, window_min: int = 15) -> Optional[Dict]:
        """
        Main method to calculate liquidity metrics
        If symbol is None, fetches all available symbols from the microservice
        Returns dict with symbol -> metrics mapping
        """
        logger.info(f"Calculating liquidity for {symbol or 'all symbols'}")
        
        # Fetch aggregated data from Trading/Liquidity Microservice
        agg_items = self.fetch_liquidity_input(window_min=window_min)
        
        if not agg_items:
            logger.error("No liquidity input data available")
            return None
        
        logger.info(f"Received {len(agg_items)} symbols to process")
        
        results = {}
        
        for item in agg_items:
            item_symbol = item.get('symbol')
            
            # If specific symbol requested, skip others
            if symbol and item_symbol != symbol:
                continue
            
            metrics = self.calculate_metrics_from_aggregated_data(item)
            
            if metrics:
                results[item_symbol] = {
                    'metrics': metrics,
                    'trades_count': int(item.get('trades_count', 0)),
                    'volume_usd': float(item.get('volume_usd', 0))
                }
        
        # If specific symbol requested, return just that one
        if symbol:
            return results.get(symbol)
        
        return results