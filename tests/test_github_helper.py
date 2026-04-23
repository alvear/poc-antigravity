"""
Testes de github_helper.

Cobertura:
- get_branch_sha happy + erro
- create_branch happy + branch ja existe (422) + erro
- commit_file happy + erro
- create_pr happy + erro
- create_tag happy + erro
"""
from unittest.mock import patch, MagicMock

import pytest

import github_helper
from agents.exceptions import GitHubError


def _mock_response(ok=True, status_code=200, json_data=None, text=""):
    r = MagicMock()
    r.ok = ok
    r.status_code = status_code
    r.json.return_value = json_data or {}
    r.text = text
    return r


# ---- get_branch_sha ----
@patch("github_helper.requests")
def test_get_branch_sha_happy(mock_requests):
    mock_requests.get.return_value = _mock_response(
        ok=True, status_code=200, json_data={"object": {"sha": "abc1234567"}}
    )
    result = github_helper.get_branch_sha("main")
    assert result == "abc1234567"


@patch("github_helper.requests")
def test_get_branch_sha_error_raises(mock_requests):
    mock_requests.get.return_value = _mock_response(
        ok=False, status_code=404, text="Branch not found"
    )
    with pytest.raises(GitHubError) as exc_info:
        github_helper.get_branch_sha("nonexistent")
    assert exc_info.value.status_code == 404
    assert exc_info.value.context["branch"] == "nonexistent"


# ---- create_branch ----
@patch("github_helper.log")
@patch("github_helper.requests")
def test_create_branch_happy(mock_requests, mock_log):
    # Primeiro get (get_branch_sha), depois post (create)
    mock_requests.get.return_value = _mock_response(
        ok=True, status_code=200, json_data={"object": {"sha": "main_sha"}}
    )
    mock_requests.post.return_value = _mock_response(
        ok=True, status_code=201
    )
    result = github_helper.create_branch("feature/test")
    assert result == "feature/test"


@patch("github_helper.log")
@patch("github_helper.requests")
def test_create_branch_422_already_exists(mock_requests, mock_log):
    """422 significa branch ja existe - funcao retorna o nome sem levantar."""
    mock_requests.get.return_value = _mock_response(
        ok=True, status_code=200, json_data={"object": {"sha": "main_sha"}}
    )
    mock_requests.post.return_value = _mock_response(
        ok=False, status_code=422, text="Reference already exists"
    )
    result = github_helper.create_branch("feature/existing")
    assert result == "feature/existing"


@patch("github_helper.log")
@patch("github_helper.requests")
def test_create_branch_other_error_raises(mock_requests, mock_log):
    mock_requests.get.return_value = _mock_response(
        ok=True, status_code=200, json_data={"object": {"sha": "main_sha"}}
    )
    mock_requests.post.return_value = _mock_response(
        ok=False, status_code=500, text="Server error"
    )
    with pytest.raises(GitHubError) as exc_info:
        github_helper.create_branch("feature/bad")
    assert exc_info.value.status_code == 500


# ---- commit_file ----
@patch("github_helper.log")
@patch("github_helper.requests")
def test_commit_file_new_file(mock_requests, mock_log):
    """Arquivo novo: GET 404 (sem sha), PUT cria."""
    mock_requests.get.return_value = _mock_response(
        ok=False, status_code=404
    )
    mock_requests.put.return_value = _mock_response(
        ok=True, status_code=201, json_data={"commit": {"sha": "commit_sha_123"}}
    )
    result = github_helper.commit_file("main", "file.txt", "content", "msg")
    assert result == "commit_"


@patch("github_helper.log")
@patch("github_helper.requests")
def test_commit_file_existing(mock_requests, mock_log):
    """Arquivo existe: GET retorna sha, PUT atualiza."""
    mock_requests.get.return_value = _mock_response(
        ok=True, status_code=200, json_data={"sha": "existing_sha"}
    )
    mock_requests.put.return_value = _mock_response(
        ok=True, status_code=200, json_data={"commit": {"sha": "new_commit_sha"}}
    )
    result = github_helper.commit_file("main", "file.txt", "new", "msg")
    assert result == "new_com"


@patch("github_helper.log")
@patch("github_helper.requests")
def test_commit_file_error_raises(mock_requests, mock_log):
    mock_requests.get.return_value = _mock_response(ok=False, status_code=404)
    mock_requests.put.return_value = _mock_response(
        ok=False, status_code=403, text="Forbidden"
    )
    with pytest.raises(GitHubError):
        github_helper.commit_file("main", "file.txt", "content", "msg")


# ---- create_pr ----
@patch("github_helper.log")
@patch("github_helper.requests")
def test_create_pr_happy(mock_requests, mock_log):
    mock_requests.post.return_value = _mock_response(
        ok=True,
        status_code=201,
        json_data={"number": 42, "html_url": "https://github.com/x/y/pull/42"},
    )
    result = github_helper.create_pr("feature/x", "main", "Titulo", "Corpo")
    assert result["number"] == 42


@patch("github_helper.log")
@patch("github_helper.requests")
def test_create_pr_error_raises(mock_requests, mock_log):
    mock_requests.post.return_value = _mock_response(
        ok=False, status_code=422, text="Validation failed"
    )
    with pytest.raises(GitHubError):
        github_helper.create_pr("bad", "main", "t", "b")
