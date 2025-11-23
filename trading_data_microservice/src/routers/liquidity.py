from fastapi import APIRouter, Depends, Query
from ..auth import enforce_api_key
from ..db import get_conn

router = APIRouter()

@router.get("/liquidity/input")
def liq_input(window_min: int = Query(15, ge=1, le=1440),
              limit_symbols: int = Query(6, ge=1, le=50),
              _auth=Depends(enforce_api_key)):
    sql = """
    SELECT symbol,
           COUNT(*) AS trades_count,
           SUM(price * quantity)::numeric(24,8) AS volume_usd
    FROM transactions
    WHERE to_timestamp(unix_time) >= NOW() - INTERVAL %s
    GROUP BY symbol
    ORDER BY 3 DESC
    LIMIT %s;
    """
    # with get_conn() as c, c.cursor() as cur:
    #     cur.execute(sql, (f"{window_min} minutes", limit_symbols))
    #     rows = [{"symbol": s, "trades_count": int(tc), "volume_usd": str(v or 0)} for s, tc, v in cur.fetchall()]
    # return {"items": rows, "window_min": window_min}

    try:
        with get_conn() as c, c.cursor() as cur:
            cur.execute(sql, (f"{window_min} minutes", limit_symbols))
            rows = cur.fetchall()
        items = [
            {"symbol": r[0], "trades_count": int(r[1] or 0), "volume_usd": str(r[2] or 0)}
            for r in rows
        ]
        return {"items": items, "window_min": window_min}
    except Exception:
        return {"items": [], "window_min": window_min}

@router.get("/liquidity/last_update")
def liq_last_update(_auth=Depends(enforce_api_key)):
    sql = "SELECT to_timestamp(MAX(window_end_unix)) FROM liquidity_results"
    with get_conn() as c, c.cursor() as cur:
        cur.execute(sql)
        row = cur.fetchone()
    return {"last_update_utc": row[0].isoformat() if row and row[0] else None}

@router.post("/liquidity/result")
def liq_result(payload: dict, _auth=Depends(enforce_api_key)):
    required = ["job_id","window_start_unix","window_end_unix","results"]
    for k in required:
        if k not in payload:
            return {"error": f"missing {k}"}
    rows = payload["results"] or []
    if not rows:
        return {"inserted": 0}

    sql = """
    INSERT INTO liquidity_results(job_id,symbol,window_start_unix,window_end_unix,
                                  volume_usd,trades_count,liq_score)
    VALUES (%s,%s,%s,%s,%s,%s,%s)
    ON CONFLICT (job_id, symbol, window_start_unix, window_end_unix)
    DO UPDATE SET volume_usd=EXCLUDED.volume_usd,
                  trades_count=EXCLUDED.trades_count,
                  liq_score=EXCLUDED.liq_score;
    """
    with get_conn() as c, c.cursor() as cur:
        for r in rows:
            cur.execute(sql, (
                payload["job_id"], r["symbol"],
                payload["window_start_unix"], payload["window_end_unix"],
                r.get("volume_usd","0"), int(r.get("trades_count",0)),
                r.get("liq_score","0"),
            ))
        c.commit()
    return {"inserted": len(rows)}
