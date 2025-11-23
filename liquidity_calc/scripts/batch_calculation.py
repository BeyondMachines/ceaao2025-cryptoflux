import os
import time
import requests
import sys
from datetime import datetime

# Add the parent directory to Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from liquidity_calculator import LiquidityCalculator

def post_results_to_listener(results, window_min=15):
    """
    Post calculated liquidity results back to Trading/Liquidity Microservice
    results: list of dicts with symbol, metrics, trades_count, volume_usd
    """
    trading_data_api_key = os.getenv("TRADING_DATA_API_KEY")
    if not trading_data_api_key:
        print("TRADING_DATA_API_KEY not set; skipping POST to listener")
        return

    trading_data_url = os.getenv("TRADING_DATA_URL", "http://localhost:7100")
    url = f"{trading_data_url}/api/v1/liquidity/result"

    now = int(time.time())
    window_seconds = window_min * 60
    
    payload = {
        "job_id": f"job-{now}",
        "window_start_unix": now - window_seconds,
        "window_end_unix": now,
        "results": [
            {
                "symbol": r["symbol"],
                "volume_usd": str(r.get('volume_usd', 0)),
                "trades_count": int(r.get("trades_count", 0)),
                "liq_score": f"{r['liq_score']:.2f}",
            }
            for r in results
            if r.get("liq_score") != "FAILED"
        ],
    }

    try:
        resp = requests.post(
            url,
            json=payload,
            headers={
                "X-API-Key": trading_data_api_key,
                "Content-Type": "application/json"
            },
            timeout=20,
        )
        print(f"POST /liquidity/result: {resp.status_code}")
        print(f"Response: {resp.text}")
        
        if resp.status_code == 200:
            print("✓ Successfully posted liquidity results")
        else:
            print(f"✗ Failed to post results: {resp.status_code}")
            
    except Exception as e:
        print(f"Error posting results: {e}")

def main():
    # Get API key for Trading/Liquidity Microservice
    trading_data_api_key = os.getenv('TRADING_DATA_API_KEY')
    if not trading_data_api_key:
        print("ERROR: TRADING_DATA_API_KEY environment variable not set")
        sys.exit(1)
    
    # Get Trading Data URL
    trading_data_url = os.getenv('TRADING_DATA_URL', 'http://localhost:7100')
    
    # Get window size (default 15 minutes)
    window_min_str = os.getenv('LIQ_WINDOW_MIN', '15')
    try:
        window_min = int(window_min_str)
    except ValueError:
        window_min = 15  # Default if env var is malformed
    
    print(f"\n{'='*60}")
    print(f"LIQUIDITY CALCULATION")
    print(f"{'='*60}")
    print(f"Time: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')}")
    print(f"Trading Data URL: {trading_data_url}")
    print(f"Window: {window_min} minutes")
    print(f"{'='*60}\n")
    
    # Initialize calculator
    calculator = LiquidityCalculator(
        api_key=trading_data_api_key,
        trading_data_url=trading_data_url
    )
    
    # Calculate liquidity for all symbols (fetches from microservice)
    results_dict = calculator.calculate_liquidity(window_min=window_min)
    
    if not results_dict:
        print("✗ No liquidity data available")
        sys.exit(1)
    
    print(f"Successfully calculated liquidity for {len(results_dict)} symbols\n")
    
    # Format results for display and posting
    all_results = []
    
    for symbol, data in results_dict.items():
        metrics = data['metrics']
        trades_count = data['trades_count']
        volume_usd = data['volume_usd']
        
        print(f"📊 {symbol}")
        print(f"   Liquidity Score: {metrics.liquidity_score:.1f}/100")
        print(f"   Bid-Ask Spread: {metrics.bid_ask_spread:.4f}%")
        print(f"   Order Book Depth: {metrics.order_book_depth:,.2f}")
        print(f"   24h Volume: ${volume_usd:,.2f}")
        print(f"   Volatility: {metrics.volatility:.2f}%")
        print(f"   Trades Count: {trades_count}")
        print()
        
        all_results.append({
            'symbol': symbol,
            'liq_score': metrics.liquidity_score,
            'volume_usd': volume_usd,
            'trades_count': trades_count,
            'spread': metrics.bid_ask_spread
        })
    
    # Print summary
    print(f"\n{'='*60}")
    print("SUMMARY")
    print(f"{'='*60}")
    
    if all_results:
        avg_score = sum(r['liq_score'] for r in all_results) / len(all_results)
        best = max(all_results, key=lambda x: x['liq_score'])
        worst = min(all_results, key=lambda x: x['liq_score'])
        
        print(f"Symbols Analyzed: {len(all_results)}")
        print(f"Average Liquidity Score: {avg_score:.1f}/100")
        print(f"Best: {best['symbol']} ({best['liq_score']:.1f}/100)")
        print(f"Worst: {worst['symbol']} ({worst['liq_score']:.1f}/100)")
    
    # Post results back to Trading/Liquidity Microservice
    print(f"\n{'='*60}")
    print("Posting results back to Trading/Liquidity Microservice...")
    print(f"{'='*60}")
    post_results_to_listener(all_results, window_min=window_min)
    
    print(f"\n✓ Calculation complete!")

if __name__ == "__main__":
    main()