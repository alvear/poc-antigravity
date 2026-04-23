"""
Testes de confluence_helper.

Cobertura:
- _get_space_id happy + erro
- create_page happy + pagina ja existe + erro
"""
from unittest.mock import patch, MagicMock

import pytest

import confluence_helper
from agents.exceptions import ConfluenceError


def _mock_response(ok=True, status_code=200, json_data=None, text=""):
    r = MagicMock()
    r.ok = ok
    r.status_code = status_code
    r.json.return_value = json_data or {}
    r.text = text
    return r


# ---- _get_space_id ----
@patch("confluence_helper.requests")
def test_get_space_id_happy(mock_requests):
    mock_requests.get.return_value = _mock_response(
        ok=True, status_code=200,
        json_data={"results": [{"id": "space_123"}]}
    )
    result = confluence_helper._get_space_id()
    assert result == "space_123"


@patch("confluence_helper.requests")
def test_get_space_id_not_found_raises(mock_requests):
    """Space nao existe: results vazio -> RuntimeError nativo."""
    mock_requests.get.return_value = _mock_response(
        ok=True, status_code=200, json_data={"results": []}
    )
    with pytest.raises(RuntimeError, match="Space nao encontrado"):
        confluence_helper._get_space_id()


@patch("confluence_helper.requests")
def test_get_space_id_http_error_raises_confluence_error(mock_requests):
    mock_requests.get.return_value = _mock_response(
        ok=False, status_code=401, text="Unauthorized"
    )
    with pytest.raises(ConfluenceError) as exc_info:
        confluence_helper._get_space_id()
    assert exc_info.value.status_code == 401


# ---- create_page ----
@patch("confluence_helper.log")
@patch("confluence_helper.requests")
def test_create_page_happy(mock_requests, mock_log):
    """create_page sem parent: chama _get_space_id -> POST."""
    mock_requests.get.return_value = _mock_response(
        ok=True, status_code=200,
        json_data={"results": [{"id": "space_id"}]}
    )
    mock_requests.post.return_value = _mock_response(
        ok=True, status_code=200, json_data={"id": "page_123", "title": "T"}
    )
    result = confluence_helper.create_page("Titulo", "<p>body</p>")
    assert result["id"] == "page_123"


@patch("confluence_helper.log")
@patch("confluence_helper.requests")
def test_create_page_already_exists_returns_none(mock_requests, mock_log):
    """400 com 'already exists': funcao retorna None sem levantar."""
    mock_requests.get.return_value = _mock_response(
        ok=True, status_code=200,
        json_data={"results": [{"id": "space_id"}]}
    )
    mock_requests.post.return_value = _mock_response(
        ok=False, status_code=400, text="A page with this title already exists"
    )
    result = confluence_helper.create_page("Duplicada", "<p>x</p>")
    assert result is None


@patch("confluence_helper.log")
@patch("confluence_helper.requests")
def test_create_page_other_error_raises(mock_requests, mock_log):
    mock_requests.get.return_value = _mock_response(
        ok=True, status_code=200,
        json_data={"results": [{"id": "space_id"}]}
    )
    mock_requests.post.return_value = _mock_response(
        ok=False, status_code=500, text="Server error"
    )
    with pytest.raises(ConfluenceError):
        confluence_helper.create_page("T", "<p>x</p>")
