"""
Testes de gate_logger.

Cobertura:
- start_proposal cria session, retorna ID, persiste em .gate_sessions.json
- record_decision approved atualiza a session
- record_decision rejected com feedback
- compute_fpy sem sessions -> 0%
- compute_fpy com mix approved/rejected -> calcula FPY correto

Usa tmp_path + monkeypatch pra isolar .gate_sessions.json dos testes.
"""
import json
from pathlib import Path

import pytest

import gate_logger


@pytest.fixture
def isolated_sessions(tmp_path, monkeypatch):
    """Isola .gate_sessions.json num diretorio temporario por teste."""
    sessions_file = tmp_path / ".gate_sessions.json"
    monkeypatch.setattr(gate_logger, "SESSIONS_FILE", str(sessions_file))
    return sessions_file


# ---- start_proposal ----
def test_start_proposal_creates_session(isolated_sessions):
    """start_proposal cria arquivo e retorna session_id unico."""
    session_id = gate_logger.start_proposal(
        "release-agent", "release", "v1.0"
    )
    assert session_id.startswith("release-agent-release-")
    
    # Arquivo deve existir com 1 session
    data = json.loads(isolated_sessions.read_text(encoding="utf-8"))
    assert len(data) == 1
    assert data[0]["session_id"] == session_id
    assert data[0]["agent"] == "release-agent"
    assert data[0]["decision"] is None


# ---- record_decision approved ----
def test_record_decision_approved(isolated_sessions):
    sid = gate_logger.start_proposal("agent", "kind", "summary")
    gate_logger.record_decision(sid, "approved", jira_key="POC-1")
    
    data = json.loads(isolated_sessions.read_text(encoding="utf-8"))
    assert data[0]["decision"] == "approved"
    assert data[0]["jira_key"] == "POC-1"
    assert "duration_sec" in data[0]


# ---- record_decision rejected ----
def test_record_decision_rejected_with_feedback(isolated_sessions):
    sid = gate_logger.start_proposal("agent", "kind", "summary")
    gate_logger.record_decision(sid, "rejected", feedback="erro X")
    
    data = json.loads(isolated_sessions.read_text(encoding="utf-8"))
    assert data[0]["decision"] == "rejected"
    assert data[0]["feedback"] == "erro X"


# ---- compute_fpy ----
def test_compute_fpy_empty(isolated_sessions):
    """Sem sessions: fpy = 0, total = 0."""
    # Cria arquivo vazio
    isolated_sessions.write_text("[]", encoding="utf-8")
    result = gate_logger.compute_fpy()
    assert result["fpy"] == 0.0
    assert result["total"] == 0


def test_compute_fpy_all_approved(isolated_sessions):
    """3 approved primeiro pass: FPY = 100%."""
    for i in range(3):
        sid = gate_logger.start_proposal("agent", "kind", f"s{i}")
        gate_logger.record_decision(sid, "approved")
    
    result = gate_logger.compute_fpy()
    assert result["fpy"] == 100.0
    assert result["total"] == 3
    assert result["approved"] == 3


def test_compute_fpy_mixed(isolated_sessions):
    """2 approved + 1 rejected: FPY = 66.7%."""
    for i in range(2):
        sid = gate_logger.start_proposal("agent", "kind", f"a{i}")
        gate_logger.record_decision(sid, "approved")
    sid = gate_logger.start_proposal("agent", "kind", "r1")
    gate_logger.record_decision(sid, "rejected", feedback="x")
    
    result = gate_logger.compute_fpy()
    # 2 approved de 3 total = 66.66... arredondado pra 66.7
    assert result["fpy"] == pytest.approx(66.7, abs=0.1)
    assert result["total"] == 3
    assert result["approved"] == 2
