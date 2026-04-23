"""
Grafana Logger - envia logs estruturados para Loki.

Usado por todos os agentes e helpers da esteira para observabilidade.
Todo log carrega: level, agent, message, service, ts (ISO8601 UTC).
"""
import json
import sys
import time
from datetime import datetime, timezone

import requests

from config import settings

LOKI_URL = settings.grafana_loki_url
USER = settings.grafana_user
TOKEN = settings.grafana_token.get_secret_value()


def send_log(level, agent, message, extra=None):
    """Envia 1 evento estruturado para o Loki."""
    now_ns = str(int(time.time() * 1e9))
    payload = {
        "level": level.upper(),
        "agent": agent,
        "message": message,
        "service": "poc-antigravity",
        "ts": datetime.now(timezone.utc).isoformat(),
    }
    if extra:
        payload.update(extra)

    body = {
        "streams": [
            {
                "stream": {
                    "service": "poc-antigravity",
                    "agent": agent,
                    "level": level.upper(),
                    "env": "poc",
                },
                "values": [[now_ns, json.dumps(payload)]],
            }
        ]
    }

    r = requests.post(
        f"{LOKI_URL}/loki/api/v1/push",
        auth=(USER, TOKEN),
        headers={"Content-Type": "application/json"},
        json=body,
    )

    if r.status_code in (200, 204):
        print(f"[GRAFANA] {level.upper()} | {agent} | {message}")
    else:
        # Telemetria nao deve quebrar fluxo principal (observability-first).
        # Mas registra em stderr para visibilidade local/CI.
        sys.stderr.write(
            f"[GRAFANA ERROR] Status {r.status_code}: {r.text[:200]}\n"
        )


def info(agent, message, extra=None):
    send_log("info", agent, message, extra)


def warn(agent, message, extra=None):
    send_log("warn", agent, message, extra)


def error(agent, message, extra=None):
    send_log("error", agent, message, extra)


def success(agent, message, extra=None):
    send_log("info", agent, f"SUCCESS: {message}", extra)


if __name__ == "__main__":
    info("pm-agent", "Teste de conexao com Grafana Loki", {"test": True})
