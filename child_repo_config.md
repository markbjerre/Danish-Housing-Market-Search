# Child Repository Config Template

**Copy this to Finance, CV, and Finnish project repositories.**

---

## Dockerfile

```dockerfile
FROM python:3.11-slim
WORKDIR /app
RUN apt-get update && apt-get install -y --no-install-recommends gcc && rm -rf /var/lib/apt/lists/*
COPY requirements.txt . && RUN pip install --no-cache-dir -r requirements.txt
COPY . .
EXPOSE 8000
# Adjust WORKDIR if your Flask app is in a subdirectory (like webapp/)
WORKDIR /app
CMD ["gunicorn", "-w", "2", "-b", "0.0.0.0:8000", "app:app"]
```

**Note:** If Flask app is in subdirectory (e.g., `webapp/`), change last WORKDIR before CMD.

---

## requirements.txt (Minimal)

```
flask==2.3.3
werkzeug==2.3.7
gunicorn==21.2.0
flask-sqlalchemy==3.0.5
```

**Critical:** Always include gunicorn and keep Flask/Werkzeug versions aligned.

---

## docker-compose.yml - Service Entry

Add to `/root/docker-compose.yml` on VPS:

```yaml
ai-vaerksted-finance:
  build: /opt/ai-vaerksted/Finance-Dashboard
  container_name: ai-vaerksted-finance
  networks:
    - default
  environment:
    - FLASK_ENV=production
  labels:
    - traefik.enable=true
    - 'traefik.http.routers.finance.rule=Host(`ai-vaerksted.cloud`) && PathPrefix(`/finance`)'
    - traefik.http.routers.finance.entrypoints=websecure
    - traefik.http.routers.finance.tls.certresolver=mytlschallenge
    - 'traefik.http.middlewares.finance-strip.stripprefix.prefixes=/finance'
    - traefik.http.routers.finance.middlewares=finance-strip
    - traefik.http.services.finance.loadbalancer.server.port=8000
```

**Variables to change:**
- `ai-vaerksted-finance` → service name (replace "finance" with project name)
- `/opt/ai-vaerksted/Finance-Dashboard` → path to project directory
- `/finance` → URL path prefix
- Port 8000 → if different

---

## Flask App Structure

**Minimal entry point (`app.py` or `app/__init__.py`):**

```python
from flask import Flask

app = Flask(__name__)

@app.route('/')
def index():
    return "Project Name Home"

@app.route('/health')
def health():
    return {"status": "ok"}, 200

if __name__ == '__main__':
    app.run(debug=False)
```

**Key Points:**
- Entry point must be at root or in `app/` (specify in Dockerfile CMD)
- Implement `/health` endpoint for monitoring
- Use `FLASK_ENV=production` in docker-compose
- Do NOT expect URL prefix in routes (Traefik strips `/finance` before routing)

---

## GitHub Workflow

1. **Create repository** with standard structure:
   ```
   project-name/
   ├── app.py (or app/__init__.py)
   ├── Dockerfile
   ├── requirements.txt
   ├── README.md
   └── templates/ (if using Jinja2)
   ```

2. **Add to docker-compose.yml** on VPS with service template above

3. **Deploy:**
   ```bash
   cd /opt/ai-vaerksted/Finance-Dashboard
   git pull origin main
   docker build -t ai-vaerksted-finance:latest .
   cd /root
   docker-compose up -d ai-vaerksted-finance
   ```

4. **Verify:**
   ```bash
   curl https://ai-vaerksted.cloud/finance
   curl https://ai-vaerksted.cloud/finance/health
   ```

---

## Environment Variables (If Database Needed)

Add to docker-compose.yml service environment section:

```yaml
environment:
  - FLASK_ENV=production
  - DB_HOST=project-db
  - DB_PORT=5432
  - DB_NAME=projectdb
  - DB_USER=projectuser
  - DB_PASSWORD=secure_password_2024
```

Then add database service to docker-compose.yml:

```yaml
project-db:
  image: postgres:15-alpine
  container_name: project-db
  environment:
    - POSTGRES_DB=projectdb
    - POSTGRES_USER=projectuser
    - POSTGRES_PASSWORD=secure_password_2024
  volumes:
    - project_db_data:/var/lib/postgresql/data
  networks:
    - default
  healthcheck:
    test: ["CMD-SHELL", "pg_isready -U projectuser"]
    interval: 10s
    timeout: 5s
    retries: 5

volumes:
  project_db_data:
```

---

## Key Rules

✅ **DO:**
- Keep requirements.txt minimal
- Include gunicorn in requirements.txt
- Use Flask 2.3.3 + Werkzeug 2.3.7
- Implement `/health` endpoint
- Use environment variables for config
- Test with curl before deployment

❌ **DO NOT:**
- Hardcode credentials
- Use Flask 2.0.1 (incompatible with Werkzeug 2.3+)
- Expect `/finance` prefix in Flask routes
- Expose database ports externally
- Mix different Flask/Werkzeug versions

---

## Template Summary

| Item | Value |
|------|-------|
| Python | 3.11-slim |
| Flask | 2.3.3 |
| Gunicorn workers | 2 |
| Port | 8000 (internal) |
| Traefik routing | Path-based (`/finance`, `/cv`, `/finnish`) |
| SSL | Automatic via Let's Encrypt |
| Database | PostgreSQL 15-alpine (optional) |

---

**For details, see CLAUDE.md in front-page repository.**
