"""
Testes do QAAgent.

Estrategia:
- Metodo estatico _render_confluence_body testado puro (nao precisa mock)
- Metodo publico run() com mocks dos 3 helpers (github, confluence, gate_logger)
"""
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

from agents.qa import QAAgent
from agents.exceptions import ValidationError


# ============================================================
# Instanciacao
# ============================================================
def test_qa_agent_instantiates():
    agent = QAAgent()
    assert agent.AGENT_NAME == "qa-agent"


# ============================================================
# _render_confluence_body (static, sem mock)
# ============================================================
def test_render_confluence_body_contains_story_and_counts():
    body = QAAgent._render_confluence_body(
        story="POC-2",
        branch="feature/POC-2-oauth",
        total=12,
        det_count=7,
        llm_count=5,
    )
    assert "POC-2" in body
    assert "feature/POC-2-oauth" in body
    assert "12" in body  # total
    assert "7" in body   # det
    assert "5" in body   # llm
    # HTML esperado
    assert "<h1>" in body
    assert "<ul>" in body


def test_render_confluence_body_has_strategy_section():
    body = QAAgent._render_confluence_body("s", "b", 1, 1, 0)
    assert "Shift-left" in body or "shift-left" in body


# ============================================================
# run() - happy path
# ============================================================
@patch("agents.qa.confluence_helper")
@patch("agents.qa.github_helper")
@patch("agents.base.gate_logger")
@patch("agents.base.log")
def test_run_happy_path_generates_and_commits(
    mock_log, mock_gate, mock_gh, mock_conf, tmp_path, monkeypatch
):
    """Run normal: cria files, valida AST, commita 4 arquivos, publica Confluence."""
    # Isola operacoes de disco em tmp_path
    monkeypatch.chdir(tmp_path)
    # Cria requirements.txt vazio (run le esse arquivo)
    (tmp_path / "requirements.txt").write_text("fastapi\n", encoding="utf-8")
    
    mock_gate.start_proposal.return_value = "session-qa-1"
    mock_conf.create_page.return_value = {"id": "page-1"}
    
    agent = QAAgent()
    result = agent.run(branch="feature/test", story="POC-42")
    
    # Retorno estruturado
    assert result["story"] == "POC-42"
    assert result["branch"] == "feature/test"
    assert result["tests_total"] > 0
    assert result["tests_deterministic"] >= 0
    assert result["tests_llm"] >= 0
    
    # Arquivos locais foram criados
    assert (tmp_path / "tests" / "test_auth.py").exists()
    assert (tmp_path / "tests" / "conftest.py").exists()
    
    # GitHub commits - deve ter commitado pelo menos 3 arquivos de teste
    assert mock_gh.commit_file.call_count >= 3
    
    # Confluence - 1 pagina com evidencia
    mock_conf.create_page.assert_called_once()
    call_kwargs = mock_conf.create_page.call_args.kwargs
    assert "POC-42" in call_kwargs["title"]
    
    # Gate aprovado
    mock_gate.record_decision.assert_called_with(
        "session-qa-1", "approved", jira_key="POC-42"
    )


# ============================================================
# run() - defaults sao usados quando nao passa params
# ============================================================
@patch("agents.qa.confluence_helper")
@patch("agents.qa.github_helper")
@patch("agents.base.gate_logger")
@patch("agents.base.log")
def test_run_with_defaults(
    mock_log, mock_gate, mock_gh, mock_conf, tmp_path, monkeypatch
):
    """run() sem params usa defaults (feature/POC-2-...  e POC-2)."""
    monkeypatch.chdir(tmp_path)
    (tmp_path / "requirements.txt").write_text("", encoding="utf-8")
    
    mock_gate.start_proposal.return_value = "s"
    mock_conf.create_page.return_value = {"id": "p"}
    
    agent = QAAgent()
    result = agent.run()  # sem args
    
    assert result["story"] == "POC-2"
    assert "POC-2" in result["branch"]
