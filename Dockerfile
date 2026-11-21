FROM python:3.13-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    TELEMETRY_RATE_LIMIT=100

RUN pip install --no-cache-dir fastapi uvicorn

COPY src ./src
COPY pyproject.toml ./

EXPOSE 8000

CMD ["python", "-m", "telemetry.serve", "server", "--host", "0.0.0.0", "--port", "8000"]
