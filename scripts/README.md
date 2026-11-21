# Telemetry Stream — Local Stack Scripts

Run the whole product locally with zero external dependencies (in-memory bus,
local filesystem lakehouse).

## Quick start

```bash
# 1. Start everything: server + sample events + consumer
./scripts/run_all.sh

# 2. Hit the API directly
curl http://127.0.0.1:8000/v1/telemetry?device_id=device-42
curl http://127.0.0.1:8000/v1/devices
curl http://127.0.0.1:8000/v1/metrics

# 3. Stop the server
./scripts/stop.sh
```

## Individual scripts

| Script | Purpose |
|--------|---------|
| `run_backend.sh [PORT]` | Start the FastAPI API server (background) |
| `run_producer.sh [COUNT] [DELAY] [BASE_URL]` | Send sample telemetry events |
| `run_consumer.sh [ITERS] [DELAY] [LAKEHOUSE_ROOT]` | Project events + write to lakehouse |
| `run_all.sh [PORT] [EVENT_COUNT] [CONSUMER_ITERS]` | Run the full stack end-to-end |
| `stop.sh` | Stop the API server |

## API endpoints

- `POST /v1/telemetry` — ingest a telemetry event
- `GET /v1/telemetry?device_id=<id>` — list telemetry events for a device
- `GET /v1/devices` — list registered devices
- `POST /v1/devices/register` — register a new device
- `GET /v1/metrics` — accept/reject counters + consumer lag

## Lakehouse data

Written to `/tmp/telemetry-lakehouse` as JSONL files partitioned by
`device_id=<id>/event_date=<date>/`.
