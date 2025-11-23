# worker.py
import os, time, requests

PORTAL_URL = os.getenv("PORTAL_URL", "http://portal:5000")
INTERVAL_SEC = int(os.getenv("POLL_INTERVAL", "30"))

def run():
    while True:
        try:
            r = requests.post(f"{PORTAL_URL}/api/seed", timeout=20)
            print("Seed:", r.status_code, r.text[:200])
        except Exception as e:
            print("Seed error:", type(e).__name__)
        time.sleep(INTERVAL_SEC)

if __name__ == "__main__":
    run()
