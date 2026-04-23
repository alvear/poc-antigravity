"""
Testes de grafana_logger.

Cobertura:
- send_log happy path (200/204) - chama print, nao stderr
- send_log erro (500) - NAO levanta (observability-first), escreve em stderr
- info/warn/error/success delegam corretamente pra send_log
"""
import sys
from unittest.mock import patch, MagicMock

import grafana_logger


def _mock_response(status_code=200, text=""):
    r = MagicMock()
    r.status_code = status_code
    r.text = text
    return r


# ---- send_log sucesso ----
@patch("grafana_logger.requests")
def test_send_log_success_prints_stdout(mock_requests, capsys):
    mock_requests.post.return_value = _mock_response(status_code=204)
    
    grafana_logger.send_log("info", "test-agent", "mensagem teste")
    
    captured = capsys.readouterr()
    assert "[GRAFANA]" in captured.out
    assert "INFO" in captured.out
    assert "test-agent" in captured.out
    assert "mensagem teste" in captured.out
    # stderr deve estar vazio em caso de sucesso
    assert captured.err == ""


@patch("grafana_logger.requests")
def test_send_log_200_also_success(mock_requests, capsys):
    mock_requests.post.return_value = _mock_response(status_code=200)
    grafana_logger.send_log("warn", "agent", "msg")
    captured = capsys.readouterr()
    assert "[GRAFANA]" in captured.out
    assert captured.err == ""


# ---- send_log erro (stderr, NAO levanta) ----
@patch("grafana_logger.requests")
def test_send_log_500_writes_stderr_and_does_not_raise(mock_requests, capsys):
    """Observability-first: falha nao levanta excecao."""
    mock_requests.post.return_value = _mock_response(
        status_code=500, text="Internal Server Error"
    )
    
    # Nao deve levantar
    result = grafana_logger.send_log("error", "agent", "msg")
    
    captured = capsys.readouterr()
    # Erro vai pra stderr, nao stdout
    assert "[GRAFANA ERROR]" in captured.err
    assert "500" in captured.err
    assert "Internal Server Error" in captured.err
    # stdout nao tem [GRAFANA]
    assert "[GRAFANA]" not in captured.out


@patch("grafana_logger.requests")
def test_send_log_401_writes_stderr_not_raises(mock_requests, capsys):
    mock_requests.post.return_value = _mock_response(
        status_code=401, text="Unauthorized"
    )
    grafana_logger.send_log("info", "a", "m")
    captured = capsys.readouterr()
    assert "[GRAFANA ERROR]" in captured.err
    assert "401" in captured.err


# ---- proxies (info/warn/error/success delegam) ----
@patch("grafana_logger.send_log")
def test_info_delegates(mock_send):
    grafana_logger.info("agent", "msg", {"k": "v"})
    mock_send.assert_called_once_with("info", "agent", "msg", {"k": "v"})


@patch("grafana_logger.send_log")
def test_warn_delegates(mock_send):
    grafana_logger.warn("agent", "msg")
    mock_send.assert_called_once_with("warn", "agent", "msg", None)


@patch("grafana_logger.send_log")
def test_error_delegates(mock_send):
    grafana_logger.error("agent", "msg")
    mock_send.assert_called_once_with("error", "agent", "msg", None)


@patch("grafana_logger.send_log")
def test_success_adds_prefix(mock_send):
    """success() prefixa mensagem com SUCCESS:."""
    grafana_logger.success("agent", "terminou bem")
    mock_send.assert_called_once_with("info", "agent", "SUCCESS: terminou bem", None)
