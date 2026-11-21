"""Local stack entry point for the telemetry-stream product.

Wires all four features (ingestion, stream processing, lakehouse storage,
device management) together behind the FastAPI HTTP adapter, using in-memory
adapters so the stack runs with zero external dependencies.

Usage:
    python -m telemetry.serve server          # start the API server
    python -m telemetry.serve producer        # send sample telemetry events
    python -m telemetry.serve consumer        # project + write to lakehouse
    python -m telemetry.serve all             # run server + producer + consumer
"""

from __future__ import annotations

import argparse
import json
import sys
import time
import urllib.request
from datetime import datetime, timezone

from telemetry.application.ingest import IngestTelemetry
from telemetry.device.application.use_cases import (
    CredentialApplication,
    DeviceApplication,
)
from telemetry.domain.model import TelemetryIngestion
from telemetry.domain.ports import Clock, TelemetryBus
from telemetry.infrastructure.http_adapter import TelemetryMetrics, create_app
from telemetry.infrastructure.in_memory_bus import InMemoryTelemetryBus
from telemetry.device.infrastructure.in_memory_registry import (
    InMemoryDeviceRegistry,
    InMemoryCredentialStore,
)
from telemetry.device.domain.model import DeviceManagement
from telemetry.stream.domain.model import ProjectTelemetry, ProjectTelemetryCommand
from telemetry.stream.infrastructure.in_memory_projection import (
    InMemoryTelemetryProjection,
)
from telemetry.stream.infrastructure.json_schema_adapter import (
    JsonSchemaAdapter as StreamSchema,
)
from telemetry.lakehouse.domain.model import WriteTelemetry, WriteTelemetryCommand
from telemetry.lakehouse.infrastructure.local_storage import LocalLakehouseStorage
from telemetry.lakehouse.infrastructure.local_catalog import LocalLakehouseCatalog


class SystemClock(Clock):
    def now(self) -> datetime:
        return datetime.now(timezone.utc)


def build_stack(lakehouse_root: str = "/tmp/telemetry-lakehouse"):
    """Build the full wired stack with in-memory adapters."""
    clock = SystemClock()
    bus = InMemoryTelemetryBus()

    from telemetry.infrastructure.json_schema_adapter import (
        JsonSchemaAdapter as IngestSchema,
    )

    ingestion = TelemetryIngestion(bus=bus, schema=IngestSchema(), clock=clock)
    ingest_telemetry = IngestTelemetry(ingestion=ingestion, clock=clock)

    registry = InMemoryDeviceRegistry()
    credentials = InMemoryCredentialStore()
    device_management = DeviceManagement(
        registry=registry, credentials=credentials, clock=clock
    )
    device_app = DeviceApplication(device_management=device_management)
    credential_app = CredentialApplication(
        device_management=device_management
    )

    projection = InMemoryTelemetryProjection()
    stream_schema = StreamSchema()
    project_telemetry = ProjectTelemetry(
        projection=projection, schema=stream_schema, clock=clock
    )

    storage = LocalLakehouseStorage(root_dir=lakehouse_root)
    catalog = LocalLakehouseCatalog()
    write_telemetry = WriteTelemetry(
        storage=storage, catalog=catalog, clock=clock
    )

    metrics = TelemetryMetrics()

    app = create_app(
        ingest_telemetry=ingest_telemetry,
        bus=bus,
        device_app=device_app,
        credential_app=credential_app,
        metrics=metrics,
    )

    return {
        "app": app,
        "bus": bus,
        "clock": clock,
        "ingestion": ingestion,
        "ingest_telemetry": ingest_telemetry,
        "device_app": device_app,
        "credential_app": credential_app,
        "device_management": device_management,
        "projection": projection,
        "project_telemetry": project_telemetry,
        "write_telemetry": write_telemetry,
        "storage": storage,
        "catalog": catalog,
        "metrics": metrics,
    }


def run_server(host: str = "127.0.0.1", port: int = 8000) -> None:
    """Start the FastAPI API server."""
    try:
        import uvicorn
    except ImportError:
        print("uvicorn is required to run the server: pip install uvicorn fastapi")
        sys.exit(1)

    stack = build_stack()
    uvicorn.run(stack["app"], host=host, port=port)


def run_producer(count: int = 5, delay: float = 1.0, base_url: str = "http://127.0.0.1:8000") -> None:
    """Send sample telemetry events to the running API.

    All sample payloads include the required schema fields:
    ``reading_type`` (str) and ``value`` (number).
    """
    devices = ["device-42", "device-99", "device-77"]
    readings = [
        {"reading_type": "temperature", "value": 22.5, "unit": "celsius"},
        {"reading_type": "humidity", "value": 45.0, "unit": "percent"},
        {"reading_type": "gps", "value": 1.0, "lat": 40.7128, "lon": -74.0060},
        {"reading_type": "emergency_incident", "value": 9.0, "severity": "high", "code": "FIRE_ALARM"},
        {"reading_type": "air_quality", "value": 12.0, "unit": "ug_m3"},
    ]

    print(f"Producing {count} telemetry events to {base_url} ...")
    for i in range(count):
        device = devices[i % len(devices)]
        reading = readings[i % len(readings)]
        body = json.dumps(
            {
                "device_id": device,
                "sequence": i + 1,
                "payload": reading,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
        ).encode("utf-8")
        req = urllib.request.Request(
            f"{base_url}/v1/telemetry",
            data=body,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(req) as resp:
                text = resp.read().decode("utf-8")
                print(f"  [{i+1}/{count}] {device} -> {resp.status} {text}")
        except Exception as exc:  # noqa: BLE001
            print(f"  [{i+1}/{count}] {device} -> ERROR: {exc}")
        time.sleep(delay)
    print("Done.")


def _fetch_events(base_url: str, device_id: str | None = None) -> list[dict]:
    """Fetch telemetry events from the running API."""
    url = base_url + "/v1/telemetry"
    if device_id is not None:
        url += f"?device_id={urllib.parse.quote(device_id)}"
    try:
        with urllib.request.urlopen(url) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            return data.get("events", [])
    except Exception:
        return []


def run_consumer(
    iterations: int = 10,
    delay: float = 1.0,
    lakehouse_root: str = "/tmp/telemetry-lakehouse",
    base_url: str = "http://127.0.0.1:8000",
) -> None:
    """Fetch events from the API, project device state, and write to lakehouse."""
    import urllib.parse

    stack = build_stack(lakehouse_root=lakehouse_root)
    projection = stack["projection"]
    project_telemetry = stack["project_telemetry"]
    write_telemetry = stack["write_telemetry"]
    catalog = stack["catalog"]

    print(f"Consuming events from {base_url} (lakehouse: {lakehouse_root}) ...")
    seen_offsets: set[tuple[str, int]] = set()

    for i in range(iterations):
        events = _fetch_events(base_url)
        new_events = 0
        for event in events:
            key = (event["device_id"], event["offset"])
            if key in seen_offsets:
                continue
            seen_offsets.add(key)
            new_events += 1

            cmd = ProjectTelemetryCommand(
                device_id=event["device_id"],
                sequence=event["sequence"],
                payload=event["payload"],
                offset=event["offset"],
                timestamp=datetime.fromisoformat(event["timestamp"]),
            )
            result = project_telemetry.project(cmd)

            write_cmd = WriteTelemetryCommand(
                device_id=event["device_id"],
                sequence=event["sequence"],
                offset=event["offset"],
                event_date=datetime.fromisoformat(event["timestamp"]).strftime("%Y-%m-%d"),
                payload=event["payload"],
            )
            write_result = write_telemetry.write(write_cmd)
            catalog.register_table(
                f"telemetry_{event['device_id'].replace('-', '_')}",
                write_result.partition_path,
            )
            print(
                f"  [{i+1}/{iterations}] {event['device_id']} seq={event['sequence']} "
                f"projected={result.projected} written={write_result.written}"
            )
        if new_events == 0:
            print(f"  [{i+1}/{iterations}] no new events")
        time.sleep(delay)
    print("Done.")


def run_all(port: int = 8000, event_count: int = 5, consumer_iters: int = 5) -> None:
    """Run the full stack: server, producer, consumer."""
    import subprocess
    import time as _time

    repo_dir = "/home/kali/factory/openharness/sources/telemetry-stream"
    base_url = f"http://127.0.0.1:{port}"

    print("=== Telemetry Stream Local Stack ===")
    print()

    print(f"[1/3] Starting API server on {base_url} ...")
    proc = subprocess.Popen(
        [sys.executable, "-m", "telemetry.serve", "server", "--host", "127.0.0.1", "--port", str(port)],
        cwd=repo_dir,
        env={**__import__("os").environ, "PYTHONPATH": f"{repo_dir}/src"},
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )

    # Wait for server
    for _ in range(60):
        try:
            urllib.request.urlopen(base_url + "/v1/devices")
            break
        except Exception:
            _time.sleep(0.5)
    else:
        print("Server failed to start")
        proc.terminate()
        sys.exit(1)
    print("  Server ready.")
    print()

    print(f"[2/3] Sending {event_count} sample telemetry events ...")
    run_producer(count=event_count, delay=0.5, base_url=base_url)
    print()

    print(f"[3/3] Running consumer ({consumer_iters} iterations) ...")
    run_consumer(iterations=consumer_iters, delay=0.5, lakehouse_root="/tmp/telemetry-lakehouse", base_url=base_url)
    print()

    print("=== Stack complete ===")
    print(f"API server still running on {base_url} (PID: {proc.pid})")
    print("Lakehouse data written to /tmp/telemetry-lakehouse")
    print("Run './scripts/stop.sh' to shut down the server.")
    proc.wait()


def main() -> None:
    parser = argparse.ArgumentParser(description="Telemetry Stream local stack")
    sub = parser.add_subparsers(dest="command", required=True)

    srv = sub.add_parser("server", help="start the API server")
    srv.add_argument("--host", default="127.0.0.1")
    srv.add_argument("--port", type=int, default=8000)

    prod = sub.add_parser("producer", help="send sample telemetry events")
    prod.add_argument("--count", type=int, default=5)
    prod.add_argument("--delay", type=float, default=1.0)
    prod.add_argument("--base-url", default="http://127.0.0.1:8000")

    cons = sub.add_parser("consumer", help="fetch events from API and write to lakehouse")
    cons.add_argument("--iterations", type=int, default=10)
    cons.add_argument("--delay", type=float, default=1.0)
    cons.add_argument("--lakehouse-root", default="/tmp/telemetry-lakehouse")
    cons.add_argument("--base-url", default="http://127.0.0.1:8000")

    all_cmd = sub.add_parser("all", help="run server + producer + consumer")
    all_cmd.add_argument("--port", type=int, default=8000)
    all_cmd.add_argument("--event-count", type=int, default=5)
    all_cmd.add_argument("--consumer-iters", type=int, default=5)

    args = parser.parse_args()

    if args.command == "server":
        run_server(host=args.host, port=args.port)
    elif args.command == "producer":
        run_producer(count=args.count, delay=args.delay, base_url=args.base_url)
    elif args.command == "consumer":
        run_consumer(
            iterations=args.iterations,
            delay=args.delay,
            lakehouse_root=args.lakehouse_root,
            base_url=args.base_url,
        )
    elif args.command == "all":
        run_all(port=args.port, event_count=args.event_count, consumer_iters=args.consumer_iters)


if __name__ == "__main__":
    main()
