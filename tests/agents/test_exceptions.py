"""
Testes da hierarquia de excecoes.

Cobertura:
- Heranca correta (todas extendem AntigravityError)
- HelperError carrega helper/status_code/context
- AgentError carrega agent/context
- Mensagem formatada corretamente
- isinstance checks (captura por categoria)
"""
import pytest

from agents.exceptions import (
    AntigravityError,
    HelperError,
    JiraError, JSMError, ConfluenceError, GitHubError, GrafanaError, ArchiError,
    AgentError,
    ValidationError,
    GateRejected,
    ReleaseStageFailure,
)


# ============================================================
# Hierarquia - toda excecao extende AntigravityError
# ============================================================
@pytest.mark.parametrize("exc_class", [
    HelperError, JiraError, JSMError, ConfluenceError,
    GitHubError, GrafanaError, ArchiError,
    AgentError, ValidationError, GateRejected, ReleaseStageFailure,
])
def test_all_exceptions_inherit_from_antigravity_error(exc_class):
    """Todas as excecoes devem extender AntigravityError."""
    assert issubclass(exc_class, AntigravityError)


def test_helper_exceptions_inherit_from_helper_error():
    """JiraError, GitHubError etc extendem HelperError."""
    for exc in [JiraError, JSMError, ConfluenceError, GitHubError, GrafanaError, ArchiError]:
        assert issubclass(exc, HelperError)


def test_agent_exceptions_inherit_from_agent_error():
    """ValidationError, GateRejected etc extendem AgentError."""
    for exc in [ValidationError, GateRejected, ReleaseStageFailure]:
        assert issubclass(exc, AgentError)


# ============================================================
# HelperError - estrutura de dados
# ============================================================
def test_helper_error_basic():
    """HelperError tem helper, message, sem status_code."""
    err = HelperError("jira", "Connection refused")
    assert err.helper == "jira"
    assert err.status_code is None
    assert err.context == {}
    assert "[jira]" in str(err)
    assert "Connection refused" in str(err)


def test_helper_error_with_status_and_context():
    """HelperError carrega HTTP status e contexto extra."""
    err = HelperError(
        helper="github",
        message="Branch not found",
        status_code=404,
        context={"branch": "main", "repo": "poc-antigravity"},
    )
    assert err.status_code == 404
    assert err.context["branch"] == "main"
    assert "[github]" in str(err)
    assert "HTTP 404" in str(err)


# ============================================================
# Subclasses de HelperError - helper ja pre-definido
# ============================================================
def test_jira_error_preset_helper():
    """JiraError tem helper='jira' automaticamente."""
    err = JiraError("Issue not found", status_code=404)
    assert err.helper == "jira"
    assert err.status_code == 404
    assert "[jira]" in str(err)


def test_github_error_preset_helper():
    err = GitHubError("PR already exists", status_code=422)
    assert err.helper == "github"
    assert "[github]" in str(err)


def test_archi_error_without_status_code():
    """ArchiError nao tem status HTTP (nao faz chamada API)."""
    err = ArchiError("Modelo invalido", context={"file": "model.xml"})
    assert err.helper == "archi"
    assert err.status_code is None
    assert err.context["file"] == "model.xml"


# ============================================================
# AgentError - estrutura
# ============================================================
def test_agent_error_basic():
    err = AgentError("release-agent", "No tag specified")
    assert err.agent == "release-agent"
    assert "[release-agent]" in str(err)


def test_validation_error_is_agent_error():
    err = ValidationError("qa-agent", "No tests detected in generated file")
    assert isinstance(err, AgentError)
    assert err.agent == "qa-agent"


def test_release_stage_failure_is_agent_error():
    err = ReleaseStageFailure("release-agent", "PRD stage timeout")
    assert isinstance(err, AgentError)
    assert "PRD stage timeout" in str(err)


# ============================================================
# Captura por categoria (uso real nos agentes)
# ============================================================
def test_catch_by_helper_category():
    """Uso tipico: except HelperError as e: pega qualquer helper."""
    def raises_jira():
        raise JiraError("Oops", status_code=500)
    
    try:
        raises_jira()
    except HelperError as e:
        assert e.helper == "jira"
        assert e.status_code == 500
    except Exception:
        pytest.fail("Deveria ter sido capturada como HelperError")


def test_catch_by_root_category():
    """except AntigravityError pega todas as excecoes da esteira."""
    errors_to_test = [
        JiraError("a"),
        GitHubError("b"),
        ValidationError("agent", "c"),
        GateRejected("agent", "d"),
    ]
    for err in errors_to_test:
        assert isinstance(err, AntigravityError)
