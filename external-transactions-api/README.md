# External Transactions API

External Transactions API is a containerized Python web service built with Flask and served with Gunicorn.
It provides demo crypto transaction data and enforces API key authentication.
Locally, keys are stored in a SQLite database; in production (e.g., Render), keys are loaded from environment variables.
The project includes a ready-to-use Dockerfile and Docker Compose setup for local development and deployment.

## Endpoints
- `GET /` – welcome JSON
- `GET /health` – service health
- `GET /api/v1/lookup` – list of crypto pairs (open)
- `GET /api/v1/transactions?count=5` – protected (requires `X-API-Key` header)


**Project structure:**
```
External_API/
├─ README.md
├─ app.py
├─ Dockerfile
├─ docker-compose.yml
├─ requirements.txt
└─ secrets/
   └─ api_keys.db
```

## Run Locally (Docker Compose + SQLite)

1. Clone the repository:
   ```bash
   git clone https://github.com/<username>/<repo>.git
   cd <repo>
   ```

3. Start the service:
   ```bash
   docker compose build
   docker compose up -d
   ```

4. Check health:
   ```bash
   curl http://localhost:8080/health
   ```

5. Test protected endpoint (replace `<YOUR_PLAIN_KEY>`):
   ```bash
   curl -H "X-API-Key: <YOUR_PLAIN_KEY>" "http://localhost:8080/api/v1/transactions?count=5"
   ```

> If using PowerShell:
> ```powershell
> $headers = @{ "X-API-Key" = "<YOUR_PLAIN_KEY>" }
> (Invoke-WebRequest -Uri "http://localhost:8080/api/v1/transactions" -Headers $headers).Content
> ```

---

##  Deploy on Render 

1. Push this repo to GitHub and connect it to Render.

2. In Render Dashboard → *Environment Variables* set:
   - `USE_SQLITE=False`
   - `HASHED_API_KEY=<sha256(plain+salt)>`
   - `SALT=<your_salt>`

3. Deploy. Render will build using the provided Dockerfile.

4. Test online:
   ```
   https://<service>.onrender.com/health
   https://<service>.onrender.com/api/v1/lookup
   https://<service>.onrender.com/api/v1/transactions (with header X-API-Key: <YOUR_PLAIN_KEY>)
   ```
