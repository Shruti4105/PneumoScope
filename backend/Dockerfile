FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PIP_NO_CACHE_DIR=1 PIP_DEFAULT_TIMEOUT=180 PIP_RETRIES=10
WORKDIR /srv/backend

RUN apt-get update && apt-get install -y --no-install-recommends libgl1 libglib2.0-0 curl \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install torch torchvision --index-url https://download.pytorch.org/whl/cpu \
    && pip install -r requirements.txt

COPY app ./app
COPY tests ./tests
COPY pytest.ini .

RUN useradd --create-home --uid 1000 app && mkdir -p /srv/backend/var && chown -R app /srv/backend
USER app

EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=5s --start-period=40s CMD curl -fs http://localhost:8000/health || exit 1
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--proxy-headers"]
