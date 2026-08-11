# Copenhagen apartment monitor.
#
# One image, two containers: the web UI under gunicorn, and the daily pipeline
# under cron. Both mount the same volume, because the SQLite file is the only
# thing they share.
#
# Build context is the repository root, not kbh/, because the package is
# imported as `kbh.something` and needs its parent directory on the path:
#   docker compose build --file kbh/Dockerfile .

FROM python:3.12-slim

# shapely needs GEOS. tzdata so cron and the digest agree about what "07:00"
# means, which they do not by default in a slim image running UTC.
RUN apt-get update && apt-get install -y --no-install-recommends \
        libgeos-c1v5 \
        cron \
        tzdata \
        curl \
    && rm -rf /var/lib/apt/lists/*

ENV TZ=Europe/Copenhagen \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

WORKDIR /app

COPY kbh/requirements.txt /app/kbh/requirements.txt
RUN pip install --no-cache-dir -r /app/kbh/requirements.txt gunicorn>=21.2

COPY kbh /app/kbh

# The database lives on a volume, not in the image. The cached OSM geometry is
# baked in deliberately: it is committed to the repo precisely so a deploy does
# not depend on an Overpass mirror being reachable at build time.
ENV KBH_DB_PATH=/data/kbh.sqlite3
VOLUME ["/data"]

EXPOSE 8000

# Two workers is plenty for one user, and it keeps SQLite contention trivial.
# --timeout 120 because the patterns page can ask the model a question.
CMD ["gunicorn", "--bind", "0.0.0.0:8000", "--workers", "2", "--timeout", "120", \
     "--access-logfile", "-", "--error-logfile", "-", "kbh.webapp.app:app"]
