from __future__ import annotations

import asyncio
import json
import logging
from typing import Any

from runtime.supervisor import Supervisor

log = logging.getLogger("runtime.health")


def render_metrics(snapshot: dict[str, Any]) -> str:
    lines: list[str] = []
    statuses = snapshot.get("statuses", {})
    for status, count in sorted(statuses.items()):
        lines.append(f'runtime_bots_total{{status="{status}"}} {count}')
    metrics = snapshot.get("metrics", {})
    lines.append(f"runtime_commands_total {metrics.get('commands_total', 0)}")
    lines.append(f"runtime_commands_failed_total {metrics.get('commands_failed', 0)}")
    lines.append(f"runtime_restarts_total {metrics.get('restarts_total', 0)}")
    lines.append(f"runtime_uptime_seconds {metrics.get('uptime_seconds', 0)}")
    for bot in snapshot.get("bots", []):
        labels = f'bot_id="{bot["id"]}",name="{bot["name"]}"'
        lines.append(f"runtime_bot_latency_ms{{{labels}}} {bot.get('latency_ms', 0)}")
        lines.append(f"runtime_bot_uptime_seconds{{{labels}}} {bot.get('uptime_seconds', 0)}")
    return "\n".join(lines) + "\n"


class HealthServer:
    def __init__(
        self,
        supervisor: Supervisor,
        host: str = "0.0.0.0",
        port: int = 8080,
    ) -> None:
        self._supervisor = supervisor
        self._host = host
        self._port = port
        self._server: asyncio.Server | None = None

    async def start(self) -> None:
        self._server = await asyncio.start_server(
            self._handle,
            self._host,
            self._port,
        )
        log.info("health server listening on %s:%s", self._host, self._port)

    async def close(self) -> None:
        if self._server is None:
            return
        self._server.close()
        await self._server.wait_closed()
        self._server = None

    async def _handle(self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter) -> None:
        try:
            request_line = await reader.readline()
            while True:
                line = await reader.readline()
                if line in (b"\r\n", b"\n", b""):
                    break
            if not request_line:
                return
            parts = request_line.decode("latin-1").split()
            path = parts[1] if len(parts) > 1 else "/"
            snapshot = self._supervisor.health_snapshot()
            if path == "/health":
                body = json.dumps({"status": "ok", "worker_id": snapshot["worker_id"]})
                await self._write(writer, 200, "application/json", body)
            elif path == "/ready":
                bot_statuses = snapshot.get("statuses", {})
                ready = not snapshot.get("stopping", False)
                body = json.dumps({"ready": ready, "bots": bot_statuses})
                await self._write(writer, 200 if ready else 503, "application/json", body)
            elif path == "/metrics":
                await self._write(
                    writer,
                    200,
                    "text/plain; version=0.0.4",
                    render_metrics(snapshot),
                )
            elif path == "/":
                body = json.dumps(snapshot, ensure_ascii=False)
                await self._write(writer, 200, "application/json", body)
            else:
                await self._write(writer, 404, "text/plain", "not found")
        except Exception:
            log.exception("health request failed")
        finally:
            writer.close()
            try:
                await writer.wait_closed()
            except Exception:
                pass

    async def _write(
        self,
        writer: asyncio.StreamWriter,
        status: int,
        content_type: str,
        body: str,
    ) -> None:
        payload = body.encode("utf-8")
        reason = {200: "OK", 404: "Not Found", 503: "Service Unavailable"}.get(status, "OK")
        headers = (
            f"HTTP/1.1 {status} {reason}\r\n"
            f"Content-Type: {content_type}; charset=utf-8\r\n"
            f"Content-Length: {len(payload)}\r\n"
            "Connection: close\r\n"
            "\r\n"
        )
        writer.write(headers.encode("ascii") + payload)
        await writer.drain()
