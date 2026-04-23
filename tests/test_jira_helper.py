"""
Testes de jira_helper.

Estrategia de mock:
- unittest.mock.patch em `jira_helper.requests` (o modulo importado)
- Mock objeto Response com .ok, .status_code, .json(), .text
- Mock grafana_logger.log tambem (evita chamadas reais de log)

Cenarios cobertos:
- create_issue happy path (Story, Epic, com/sem parent)
- create_issue erro HTTP -> JiraError com context
- list_issues happy path (vazio e com issues)
- list_issues erro HTTP -> JiraError
"""
from unittest.mock import patch, MagicMock

import pytest

import jira_helper
from agents.exceptions import JiraError


# ============================================================
# Helpers de teste
# ============================================================
def _mock_response(ok=True, status_code=200, json_data=None, text=""):
    """Constroi um mock do objeto Response de requests."""
    r = MagicMock()
    r.ok = ok
    r.status_code = status_code
    r.json.return_value = json_data or {}
    r.text = text
    return r


# ============================================================
# create_issue - happy path
# ============================================================
@patch("jira_helper.log")
@patch("jira_helper.requests")
def test_create_story_sem_parent(mock_requests, mock_log):
    """Cria Story sem parent_key: payload nao deve ter campo parent."""
    mock_requests.post.return_value = _mock_response(
        ok=True, status_code=201, json_data={"key": "POC-42"}
    )
    
    result = jira_helper.create_issue(
        summary="Minha Story",
        description="Descricao",
        issue_type="Story",
    )
    
    assert result == "POC-42"
    # Verifica que POST foi chamado uma vez
    assert mock_requests.post.call_count == 1
    # Verifica que payload tem o project, summary e issuetype
    call_args = mock_requests.post.call_args
    body = call_args.kwargs["json"]
    assert body["fields"]["project"]["key"] == jira_helper.PROJECT
    assert body["fields"]["summary"] == "Minha Story"
    assert body["fields"]["issuetype"]["name"] == "Story"
    # parent NAO deve estar no payload
    assert "parent" not in body["fields"]


@patch("jira_helper.log")
@patch("jira_helper.requests")
def test_create_story_com_parent(mock_requests, mock_log):
    """Cria Story com parent_key: payload deve ter campo parent."""
    mock_requests.post.return_value = _mock_response(
        ok=True, status_code=201, json_data={"key": "POC-43"}
    )
    
    result = jira_helper.create_issue(
        summary="Story vinculada",
        description="desc",
        issue_type="Story",
        parent_key="POC-1",
    )
    
    assert result == "POC-43"
    body = mock_requests.post.call_args.kwargs["json"]
    assert body["fields"]["parent"]["key"] == "POC-1"


@patch("jira_helper.log")
@patch("jira_helper.requests")
def test_create_epic(mock_requests, mock_log):
    """Cria Epic - issue_type chega correto no payload."""
    mock_requests.post.return_value = _mock_response(
        ok=True, status_code=201, json_data={"key": "POC-100"}
    )
    
    result = jira_helper.create_issue(
        summary="Grande iniciativa",
        description="desc",
        issue_type="Epic",
    )
    
    assert result == "POC-100"
    body = mock_requests.post.call_args.kwargs["json"]
    assert body["fields"]["issuetype"]["name"] == "Epic"


# ============================================================
# create_issue - erros
# ============================================================
@patch("jira_helper.log")
@patch("jira_helper.requests")
def test_create_issue_http_400_raises_jira_error(mock_requests, mock_log):
    """400 Bad Request: JiraError com status_code=400 e context."""
    mock_requests.post.return_value = _mock_response(
        ok=False, status_code=400, text="Field summary is required"
    )
    
    with pytest.raises(JiraError) as exc_info:
        jira_helper.create_issue("", "desc", "Story")
    
    err = exc_info.value
    assert err.status_code == 400
    assert err.helper == "jira"
    assert "issue_type" in err.context
    assert err.context["issue_type"] == "Story"
    assert err.context["endpoint"] == "/issue"


@patch("jira_helper.log")
@patch("jira_helper.requests")
def test_create_issue_http_500_raises_jira_error(mock_requests, mock_log):
    """500 Server Error: JiraError carrega o status e trecho do body."""
    mock_requests.post.return_value = _mock_response(
        ok=False, status_code=500, text="Internal server error at jira"
    )
    
    with pytest.raises(JiraError) as exc_info:
        jira_helper.create_issue("sum", "desc", "Story")
    
    err = exc_info.value
    assert err.status_code == 500
    # A mensagem deve conter trecho do body
    assert "Internal server error" in str(err)


@patch("jira_helper.log")
@patch("jira_helper.requests")
def test_create_issue_http_404_raises_jira_error(mock_requests, mock_log):
    """404 (project nao existe, p.ex.): JiraError com status_code=404."""
    mock_requests.post.return_value = _mock_response(
        ok=False, status_code=404, text="Project INVALID not found"
    )
    
    with pytest.raises(JiraError) as exc_info:
        jira_helper.create_issue("sum", "desc", "Story")
    
    assert exc_info.value.status_code == 404


# ============================================================
# list_issues - happy path
# ============================================================
@patch("jira_helper.log")
@patch("jira_helper.requests")
def test_list_issues_empty(mock_requests, mock_log):
    """Projeto sem issues: retorna lista vazia."""
    mock_requests.get.return_value = _mock_response(
        ok=True, status_code=200, json_data={"issues": []}
    )
    
    result = jira_helper.list_issues()
    
    assert result == []
    assert mock_requests.get.call_count == 1


@patch("jira_helper.log")
@patch("jira_helper.requests")
def test_list_issues_with_results(mock_requests, mock_log):
    """Projeto com 2 issues: retorna lista com 2 dicts shallow."""
    mock_requests.get.return_value = _mock_response(
        ok=True,
        status_code=200,
        json_data={
            "issues": [
                {
                    "key": "POC-1",
                    "fields": {
                        "summary": "Epic teste",
                        "issuetype": {"name": "Epic"},
                        "status": {"name": "A fazer"},
                    },
                },
                {
                    "key": "POC-2",
                    "fields": {
                        "summary": "Story teste",
                        "issuetype": {"name": "Story"},
                        "status": {"name": "Em andamento"},
                    },
                },
            ]
        },
    )
    
    result = jira_helper.list_issues()
    
    assert len(result) == 2
    assert result[0]["key"] == "POC-1"
    assert result[0]["type"] == "Epic"
    assert result[1]["key"] == "POC-2"
    assert result[1]["status"] == "Em andamento"


# ============================================================
# list_issues - erros
# ============================================================
@patch("jira_helper.log")
@patch("jira_helper.requests")
def test_list_issues_http_401_raises_jira_error(mock_requests, mock_log):
    """401 Unauthorized: JiraError com status=401."""
    mock_requests.get.return_value = _mock_response(
        ok=False, status_code=401, text="Invalid credentials"
    )
    
    with pytest.raises(JiraError) as exc_info:
        jira_helper.list_issues()
    
    err = exc_info.value
    assert err.status_code == 401
    assert err.context["endpoint"] == "/search"
    assert "jql" in err.context
