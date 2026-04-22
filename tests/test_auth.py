"""
Unit tests for POC Antigravity service.
Framework: pytest (equivalente ao JUnit na esteira Java).
"""
import pytest
from fastapi.testclient import TestClient
from src.main import app


client = TestClient(app)


# ============================================================
# SMOKE TESTS - carregamento da aplicacao
# ============================================================

def test_app_loads():
    """Valida que a app FastAPI carrega sem erro."""
    assert app is not None


# ============================================================
# ENDPOINT /health
# ============================================================

def test_health_returns_200():
    """GET /health deve retornar 200 OK."""
    response = client.get("/health")
    assert response.status_code == 200


def test_health_returns_json():
    """GET /health deve retornar Content-Type JSON."""
    response = client.get("/health")
    assert response.headers["content-type"].startswith("application/json")


def test_health_has_required_fields():
    """Resposta de /health deve conter status, service, env, version."""
    response = client.get("/health")
    data = response.json()
    assert data["status"] == "ok"
    assert data["service"] == "poc-antigravity"
    assert "env" in data
    assert "version" in data


def test_health_reflects_env_var(monkeypatch):
    """Campo version deve refletir a env var VERSION quando setada."""
    monkeypatch.setenv("VERSION", "v9.9.9-test")
    response = client.get("/health")
    assert response.json()["version"] == "v9.9.9-test"


# ============================================================
# ENDPOINT /
# ============================================================

def test_root_returns_200():
    """GET / deve retornar 200 OK."""
    response = client.get("/")
    assert response.status_code == 200


def test_root_has_message():
    """GET / deve retornar mensagem descritiva."""
    response = client.get("/")
    data = response.json()
    assert "message" in data
    assert "pipeline" in data["message"].lower() or "poc" in data["message"].lower()


# ============================================================
# ROTAS INVALIDAS
# ============================================================

def test_404_on_unknown_route():
    """Rota inexistente retorna 404."""
    response = client.get("/no-such-endpoint-xyz-123")
    assert response.status_code == 404


def test_method_not_allowed():
    """POST em /health (so aceita GET) retorna 405."""
    response = client.post("/health")
    assert response.status_code == 405


# ============================================================
# PERFORMANCE / IDEMPOTENCIA
# ============================================================

def test_health_is_fast():
    """Health nao pode ter dependencias lentas."""
    import time
    start = time.time()
    response = client.get("/health")
    elapsed = time.time() - start
    assert response.status_code == 200
    assert elapsed < 1.0, f"Health demorou {elapsed:.2f}s (deveria ser <1s)"


def test_health_is_idempotent():
    """/health retorna mesma estrutura em N chamadas."""
    responses = [client.get("/health").json() for _ in range(5)]
    assert all(r["status"] == "ok" for r in responses)
    assert all(r["service"] == "poc-antigravity" for r in responses)
