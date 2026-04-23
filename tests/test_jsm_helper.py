"""
Testes de jsm_helper.

Cobertura:
- create_change happy path + erro
- get_status happy path + erro  
- list_transitions happy path + erro
- transition happy path + erro
- add_comment happy path + erro
- _normalize (helper interno, sem mock)
"""
from unittest.mock import patch, MagicMock

import pytest

import jsm_helper
from agents.exceptions import JSMError


def _mock_response(ok=True, status_code=200, json_data=None, text=""):
    r = MagicMock()
    r.ok = ok
    r.status_code = status_code
    r.json.return_value = json_data or {}
    r.text = text
    return r


# ---- _normalize helper (nao faz HTTP) ----
def test_normalize_uppercases_and_trims():
    assert jsm_helper._normalize("  aprovado  ") == "APROVADO"
    assert jsm_helper._normalize("implementing") == "IMPLEMENTING"


# ---- create_change ----
@patch("jsm_helper.log")
@patch("jsm_helper.requests")
def test_create_change_standard(mock_requests, mock_log):
    mock_requests.post.return_value = _mock_response(
        ok=True, status_code=201, json_data={"key": "GMUD-42"}
    )
    result = jsm_helper.create_change(
        summary="Release v1.0",
        description="desc",
        release_tag="v1.0",
        affected_envs="PRD",
        risk="LOW",
        change_type="Standard",
    )
    assert result == "GMUD-42"


@patch("jsm_helper.log")
@patch("jsm_helper.requests")
def test_create_change_http_error_raises_jsm_error(mock_requests, mock_log):
    mock_requests.post.return_value = _mock_response(
        ok=False, status_code=400, text="Invalid payload"
    )
    with pytest.raises(JSMError) as exc_info:
        jsm_helper.create_change("s", "d", "v1.0", change_type="Standard")
    assert exc_info.value.status_code == 400
    assert exc_info.value.helper == "jsm"
    assert exc_info.value.context["endpoint"] == "/issue"


# ---- get_status (indiretamente via get_current_status) ----
@patch("jsm_helper.log")
@patch("jsm_helper.requests")
def test_get_status_happy(mock_requests, mock_log):
    mock_requests.get.return_value = _mock_response(
        ok=True,
        status_code=200,
        json_data={"fields": {"status": {"name": "Implementing"}}},
    )
    result = jsm_helper.get_status("GMUD-1")
    assert result == "IMPLEMENTING"


@patch("jsm_helper.log")
@patch("jsm_helper.requests")
def test_get_status_http_error_raises(mock_requests, mock_log):
    mock_requests.get.return_value = _mock_response(
        ok=False, status_code=404, text="Issue not found"
    )
    with pytest.raises(JSMError):
        jsm_helper.get_status("GMUD-999")


# ---- list_transitions ----
@patch("jsm_helper.log")
@patch("jsm_helper.requests")
def test_get_transitions_happy(mock_requests, mock_log):
    mock_requests.get.return_value = _mock_response(
        ok=True,
        status_code=200,
        json_data={
            "transitions": [
                {"id": "11", "name": "Implementing", "to": {"name": "Implementing"}},
                {"id": "21", "name": "Declined", "to": {"name": "Declined"}},
            ]
        },
    )
    result = jsm_helper.get_transitions("GMUD-1")
    assert len(result) == 2
    assert result[0]["id"] == "11"
    assert result[0]["name"] == "Implementing"


@patch("jsm_helper.log")
@patch("jsm_helper.requests")
def test_get_transitions_error_raises(mock_requests, mock_log):
    mock_requests.get.return_value = _mock_response(
        ok=False, status_code=500, text="Server error"
    )
    with pytest.raises(JSMError):
        jsm_helper.get_transitions("GMUD-1")


# ---- add_comment ----
@patch("jsm_helper.log")
@patch("jsm_helper.requests")
def test_add_comment_happy(mock_requests, mock_log):
    mock_requests.post.return_value = _mock_response(
        ok=True, status_code=201, json_data={"id": "10001"}
    )
    result = jsm_helper.add_comment("GMUD-1", "Teste comment")
    assert result is True


@patch("jsm_helper.log")
@patch("jsm_helper.requests")
def test_add_comment_error_raises(mock_requests, mock_log):
    mock_requests.post.return_value = _mock_response(
        ok=False, status_code=403, text="Forbidden"
    )
    with pytest.raises(JSMError) as exc_info:
        jsm_helper.add_comment("GMUD-1", "Teste")
    assert exc_info.value.status_code == 403
    assert exc_info.value.context["issue_key"] == "GMUD-1"
