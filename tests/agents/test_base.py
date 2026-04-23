"""
Testes do BaseAgent.

Cobrimos:
- AGENT_NAME obrigatorio (raises se nao definido)
- run() abstract (TypeError se nao implementar)
- Logging (proxy mensagens com AGENT_NAME correto)
- propose() em happy path (record approved no gate)
- propose() em erro (record rejected com feedback)
- propose() com set_jira_key (jira_key chega no record)
- propose() com add_context (contexto vai pro record)
- execute() chama hooks on_start / on_finish / on_error
- execute() com erro chama on_error e propaga excecao
"""
import pytest
from unittest.mock import patch, MagicMock

from agents.base import BaseAgent


# ===========================================================
# Fixture - TestAgent minimo para exercitar BaseAgent
# ===========================================================
class _MinimalAgent(BaseAgent):
    AGENT_NAME = "test-agent"
    
    def run(self, *args, **kwargs):
        return "ok"


class _FailingAgent(BaseAgent):
    AGENT_NAME = "failing-agent"
    
    def run(self):
        raise RuntimeError("simulated failure")


# ===========================================================
# Testes de contrato da classe base
# ===========================================================
def test_agent_name_obrigatorio():
    """Se AGENT_NAME vazio, instanciar deve falhar."""
    
    class _NoName(BaseAgent):
        AGENT_NAME = ""
        
        def run(self):
            pass
    
    with pytest.raises(ValueError, match="AGENT_NAME"):
        _NoName()


def test_run_abstract_forca_implementacao():
    """Nao pode instanciar classe que nao implementa run()."""
    
    with pytest.raises(TypeError, match="abstract"):
        # Nao define run() -> erro
        class _Broken(BaseAgent):
            AGENT_NAME = "broken"
        
        _Broken()


# ===========================================================
# Testes de logging
# ===========================================================
@patch("agents.base.log")
def test_log_info_proxy(mock_log):
    """log_info repassa pro grafana_logger.info com AGENT_NAME."""
    agent = _MinimalAgent()
    agent.log_info("hello", {"extra": "data"})
    mock_log.info.assert_called_once_with(
        "test-agent", "hello", {"extra": "data"}
    )


@patch("agents.base.log")
def test_log_error_proxy(mock_log):
    agent = _MinimalAgent()
    agent.log_error("oops")
    mock_log.error.assert_called_once_with("test-agent", "oops", None)


# ===========================================================
# Testes do context manager propose()
# ===========================================================
@patch("agents.base.gate_logger")
@patch("agents.base.log")
def test_propose_happy_path_marca_approved(mock_log, mock_gate):
    """Saindo do `with` sem excecao, gate deve ser approved."""
    mock_gate.start_proposal.return_value = "sid-123"
    agent = _MinimalAgent()
    
    with agent.propose("create-story", "Nova historia") as session:
        session.set_jira_key("POC-42")
    
    mock_gate.start_proposal.assert_called_once_with(
        "test-agent", "create-story", "Nova historia"
    )
    mock_gate.record_decision.assert_called_once_with(
        "sid-123", "approved", jira_key="POC-42"
    )


@patch("agents.base.gate_logger")
@patch("agents.base.log")
def test_propose_exception_marca_rejected(mock_log, mock_gate):
    """Saindo do `with` com excecao, gate deve ser rejected com feedback."""
    mock_gate.start_proposal.return_value = "sid-456"
    agent = _MinimalAgent()
    
    with pytest.raises(ValueError, match="ops"):
        with agent.propose("risky", "vai dar ruim") as session:
            session.set_jira_key("POC-99")
            raise ValueError("ops")
    
    mock_gate.record_decision.assert_called_once_with(
        "sid-456", "rejected", feedback="ops", jira_key="POC-99"
    )


@patch("agents.base.gate_logger")
@patch("agents.base.log")
def test_propose_sem_jira_key(mock_log, mock_gate):
    """propose() sem set_jira_key deve passar None."""
    mock_gate.start_proposal.return_value = "sid-abc"
    agent = _MinimalAgent()
    
    with agent.propose("review", "Revisando"):
        pass
    
    mock_gate.record_decision.assert_called_once_with(
        "sid-abc", "approved", jira_key=None
    )


@patch("agents.base.gate_logger")
@patch("agents.base.log")
def test_propose_add_context_logs(mock_log, mock_gate):
    """add_context inclui os kwargs no log de sucesso."""
    mock_gate.start_proposal.return_value = "sid-ctx"
    agent = _MinimalAgent()
    
    with agent.propose("ctx-test", "com contexto") as session:
        session.add_context(foo="bar", count=5)
    
    # Checa que log_success foi chamado com extra contendo foo e count
    mock_log.success.assert_called_once()
    call_kwargs = mock_log.success.call_args
    extra = call_kwargs[0][2]  # 3o arg posicional
    assert extra.get("foo") == "bar"
    assert extra.get("count") == 5


# ===========================================================
# Testes dos hooks e execute()
# ===========================================================
def test_execute_chama_hooks_em_ordem():
    """execute() chama on_start -> run -> on_finish."""
    
    class _HookAgent(_MinimalAgent):
        AGENT_NAME = "hook-agent"
        calls = []
        
        def on_start(self):
            self.calls.append("start")
        
        def on_finish(self, result=None):
            self.calls.append(f"finish:{result}")
        
        def run(self):
            self.calls.append("run")
            return "done"
    
    agent = _HookAgent()
    result = agent.execute()
    
    assert result == "done"
    assert agent.calls == ["start", "run", "finish:done"]


def test_execute_com_erro_chama_on_error_e_propaga():
    """execute() em excecao chama on_error e re-raise."""
    
    class _HookFail(BaseAgent):
        AGENT_NAME = "hook-fail"
        calls = []
        
        def on_start(self):
            self.calls.append("start")
        
        def on_error(self, exc):
            self.calls.append(f"error:{exc}")
        
        def run(self):
            raise RuntimeError("boom")
    
    agent = _HookFail()
    with pytest.raises(RuntimeError, match="boom"):
        agent.execute()
    
    assert agent.calls == ["start", "error:boom"]
