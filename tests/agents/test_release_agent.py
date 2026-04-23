"""
Testes do ReleaseAgent.

Estrategia:
- Metodos privados (_wait_stage, _find_run_for_tag) testados isoladamente
- Metodo publico run() testado com TODOS os helpers mockados via patch.multiple
- 2 happy paths (Standard + Normal) + 1 erro path (ReleaseStageFailure)

Agentes sao dificeis de testar porque chamam muitos helpers em cadeia.
Mockamos agressivamente para focar em LOGICA DO AGENTE, nao em integracao.
"""
from unittest.mock import patch, MagicMock, call

import pytest

from agents.release import ReleaseAgent, MAX_WAIT_STAGE_MIN
from agents.exceptions import ReleaseStageFailure


# ============================================================
# Instanciacao e heranca
# ============================================================
def test_release_agent_instantiates():
    """ReleaseAgent pode ser instanciado com AGENT_NAME setado."""
    agent = ReleaseAgent()
    assert agent.AGENT_NAME == "release-agent"


# ============================================================
# _find_run_for_tag (privado) - encontra run do deploy.yml para uma tag
# ============================================================
@patch("agents.release.github_helper")
@patch("agents.release.time")
def test_find_run_for_tag_finds_matching_branch(mock_time, mock_gh):
    """Run com head_branch == tag -> retorna imediatamente."""
    mock_time.time.return_value = 0
    mock_gh.latest_run_for_workflow.return_value = {
        "id": 123,
        "head_branch": "v1.0.0",
        "display_title": "Release",
        "html_url": "https://github.com/x/y/actions/runs/123",
    }
    agent = ReleaseAgent()
    result = agent._find_run_for_tag("v1.0.0")
    assert result["id"] == 123


@patch("agents.release.github_helper")
@patch("agents.release.time")
def test_find_run_for_tag_matches_display_title(mock_time, mock_gh):
    """Run com tag no display_title tambem casa."""
    mock_time.time.return_value = 0
    mock_gh.latest_run_for_workflow.return_value = {
        "id": 456,
        "head_branch": "main",
        "display_title": "Release v1.2.0 - feature",
        "html_url": "https://x",
    }
    agent = ReleaseAgent()
    result = agent._find_run_for_tag("v1.2.0")
    assert result["id"] == 456


# ============================================================
# _wait_stage (privado) - polling ate stage completar
# ============================================================
@patch("agents.release.github_helper")
@patch("agents.release.time")
def test_wait_stage_success(mock_time, mock_gh):
    """Stage completa com sucesso -> retorna True."""
    # time.time() retorna valores crescentes: primeiro < deadline, loop roda uma vez
    mock_time.time.side_effect = [0, 0, 100, 100]
    mock_gh.get_run_jobs.return_value = [
        {"name": "Bake image", "status": "completed", "conclusion": "success"}
    ]
    agent = ReleaseAgent()
    result = agent._wait_stage(run_id=999, stage_substr="Bake", timeout_min=1)
    assert result is True


@patch("agents.release.github_helper")
@patch("agents.release.time")
def test_wait_stage_failure_returns_false(mock_time, mock_gh):
    """Stage completa com falha -> retorna False (nao levanta)."""
    mock_time.time.side_effect = [0, 0, 100, 100]
    mock_gh.get_run_jobs.return_value = [
        {"name": "DEV deploy", "status": "completed", "conclusion": "failure"}
    ]
    agent = ReleaseAgent()
    result = agent._wait_stage(run_id=999, stage_substr="DEV", timeout_min=1)
    assert result is False


@patch("agents.release.github_helper")
@patch("agents.release.time")
def test_wait_stage_timeout_raises(mock_time, mock_gh):
    """Deadline expira sem stage completar -> TimeoutError."""
    # Simula deadline expirada imediatamente
    mock_time.time.side_effect = [0, 9999, 9999]
    mock_gh.get_run_jobs.return_value = [
        {"name": "Bake", "status": "in_progress", "conclusion": None}
    ]
    agent = ReleaseAgent()
    with pytest.raises(TimeoutError, match="timeout esperando"):
        agent._wait_stage(run_id=1, stage_substr="Bake", timeout_min=0)


# ============================================================
# run() - happy path Standard (risk=LOW)
# ============================================================
@patch("agents.release.time.sleep")  # pula sleeps
@patch("agents.release.confluence_helper")
@patch("agents.release.jsm_helper")
@patch("agents.release.github_helper")
@patch("agents.base.gate_logger")
@patch("agents.base.log")
def test_run_standard_happy_path(
    mock_log, mock_gate, mock_gh, mock_jsm, mock_conf, mock_sleep
):
    """risk=LOW -> Standard Change, auto-transition, PRD concluido."""
    # Setup mocks
    mock_gate.start_proposal.return_value = "session-123"
    mock_gh.create_tag.return_value = "v1.0.0"
    mock_gh.latest_run_for_workflow.return_value = {
        "id": 42, "head_branch": "v1.0.0",
        "display_title": "Release", "html_url": "https://x",
    }
    # _wait_stage precisa retornar True 4 vezes (Bake, DEV, UAT, PRD)
    mock_gh.get_run_jobs.return_value = [
        {"name": "Bake", "status": "completed", "conclusion": "success"},
        {"name": "DEV", "status": "completed", "conclusion": "success"},
        {"name": "UAT", "status": "completed", "conclusion": "success"},
        {"name": "PRD", "status": "completed", "conclusion": "success"},
    ]
    mock_jsm.create_change.return_value = "GMUD-10"
    mock_conf.create_page.return_value = {"id": "page-id"}
    
    agent = ReleaseAgent()
    result = agent.run(
        release_tag="v1.0.0",
        summary="Feature X",
        jira_story_key="POC-5",
        risk="LOW",
    )
    
    # Verificacoes
    assert result["release_tag"] == "v1.0.0"
    assert result["gmud_key"] == "GMUD-10"
    
    # Deve ter criado tag, GMUD, auto-transicionado, marcado done
    mock_gh.create_tag.assert_called_once()
    mock_jsm.create_change.assert_called_once()
    # Para Standard, auto-transition vai direto para Implementing
    mock_jsm.auto_transition_to_implementing.assert_called()
    mock_jsm.mark_done.assert_called_once_with("GMUD-10")
    # Release notes publicadas
    mock_conf.create_page.assert_called()
    # Gate aprovado
    mock_gate.record_decision.assert_called_with(
        "session-123", "approved", jira_key="POC-5"
    )


# ============================================================
# run() - happy path Normal (risk=HIGH) - CAB path
# ============================================================
@patch("agents.release.time.sleep")
@patch("agents.release.confluence_helper")
@patch("agents.release.jsm_helper")
@patch("agents.release.github_helper")
@patch("agents.base.gate_logger")
@patch("agents.base.log")
def test_run_normal_happy_path(
    mock_log, mock_gate, mock_gh, mock_jsm, mock_conf, mock_sleep
):
    """risk=HIGH -> Normal Change, vai ate REVISAR, aguarda CAB."""
    mock_gate.start_proposal.return_value = "session-456"
    mock_gh.create_tag.return_value = "v1.1.0"
    mock_gh.latest_run_for_workflow.return_value = {
        "id": 43, "head_branch": "v1.1.0",
        "display_title": "Release", "html_url": "https://x",
    }
    mock_gh.get_run_jobs.return_value = [
        {"name": "Bake", "status": "completed", "conclusion": "success"},
        {"name": "DEV", "status": "completed", "conclusion": "success"},
        {"name": "UAT", "status": "completed", "conclusion": "success"},
        {"name": "PRD", "status": "completed", "conclusion": "success"},
    ]
    mock_jsm.create_change.return_value = "GMUD-11"
    
    agent = ReleaseAgent()
    result = agent.run(
        release_tag="v1.1.0",
        summary="Mudanca critica",
        risk="HIGH",
    )
    
    assert result["release_tag"] == "v1.1.0"
    # Normal usa path Planejamento -> Revisar
    calls = mock_jsm.auto_transition_to_implementing.call_args_list
    assert any(
        "path" in c.kwargs and c.kwargs["path"] == ["Planejamento", "Revisar"]
        for c in calls
    )


# ============================================================
# run() - erro: run do deploy.yml nao encontrado
# ============================================================
@patch("agents.release.time")  # mocka time inteiro (.time e .sleep)
@patch("agents.release.confluence_helper")
@patch("agents.release.jsm_helper")
@patch("agents.release.github_helper")
@patch("agents.base.gate_logger")
@patch("agents.base.log")
def test_run_no_deploy_run_raises_release_stage_failure(
    mock_log, mock_gate, mock_gh, mock_jsm, mock_conf, mock_time
):
    """Se nao acha run do deploy.yml -> ReleaseStageFailure + gate rejected."""
    # time.time() retorna valores que fazem deadline expirar rapido em _find_run_for_tag
    # (time retorna 0 inicialmente, depois 99999 para deadline expirar)
    mock_time.time.side_effect = [0, 0, 99999, 99999, 99999]
    mock_gate.start_proposal.return_value = "session-err"
    mock_gh.create_tag.return_value = "v1.2.0"
    mock_gh.latest_run_for_workflow.return_value = None  # nunca acha
    
    agent = ReleaseAgent()
    with pytest.raises(ReleaseStageFailure, match="run do deploy.yml"):
        agent.run(release_tag="v1.2.0", summary="s")
    
    # Gate deve ter sido fechado como rejected
    mock_gate.record_decision.assert_called()
    last_call = mock_gate.record_decision.call_args
    assert last_call.args[1] == "rejected"
