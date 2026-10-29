# Hooqed v0: one web service (FastAPI + in-process build worker) with headless Chrome for the pipeline.
FROM python:3.13-slim-bookworm
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 DATA_DIR=/data PORT=10000
# The engine launches Chrome at /usr/bin/google-chrome, so install Google Chrome stable (brings its own system libs).
RUN apt-get update && apt-get install -y --no-install-recommends wget ca-certificates libcairo2 fonts-liberation \
 && wget -q -O /tmp/chrome.deb https://dl.google.com/linux/direct/google-chrome-stable_current_amd64.deb \
 && apt-get install -y --no-install-recommends /tmp/chrome.deb && rm /tmp/chrome.deb \
 && rm -rf /var/lib/apt/lists/*
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
EXPOSE 10000
CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-10000} --workers 1 --proxy-headers --forwarded-allow-ips='*'"]
