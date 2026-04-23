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


# ============================================================
# Testes das funcoes do Reviewer Agent (Bloco C)
# ============================================================

# ---- list_open_prs ----
@patch("github_helper.requests")
def test_list_open_prs_happy(mock_requests):
    mock_requests.get.return_value = _mock_response(
        ok=True, status_code=200,
        json_data=[
            {
                "number": 42,
                "title": "feat: add login",
                "user": {"login": "alvear"},
                "head": {"ref": "feature/login"},
                "base": {"ref": "main"},
                "html_url": "https://github.com/alvear/poc-antigravity/pull/42",
            },
            {
                "number": 43,
                "title": "fix: bug",
                "user": {"login": "bot"},
                "head": {"ref": "hotfix/bug"},
                "base": {"ref": "main"},
                "html_url": "https://github.com/alvear/poc-antigravity/pull/43",
            },
        ],
    )
    result = github_helper.list_open_prs()
    assert len(result) == 2
    assert result[0]["number"] == 42
    assert result[0]["title"] == "feat: add login"
    assert result[0]["user"] == "alvear"
    assert result[0]["head_ref"] == "feature/login"
    assert result[0]["base_ref"] == "main"
    assert "html_url" in result[0]


@patch("github_helper.requests")
def test_list_open_prs_empty(mock_requests):
    mock_requests.get.return_value = _mock_response(
        ok=True, status_code=200, json_data=[]
    )
    result = github_helper.list_open_prs()
    assert result == []


@patch("github_helper.requests")
def test_list_open_prs_http_error(mock_requests):
    mock_requests.get.return_value = _mock_response(
        ok=False, status_code=500, text="Internal Server Error"
    )
    with pytest.raises(GitHubError) as exc_info:
        github_helper.list_open_prs()
    assert exc_info.value.status_code == 500
    assert exc_info.value.context["operation"] == "list_open_prs"


# ---- get_pr_diff ----
@patch("github_helper.requests")
def test_get_pr_diff_happy(mock_requests):
    diff_text = "diff --git a/file.py b/file.py\n+print('hello')\n"
    mock_resp = _mock_response(ok=True, status_code=200, text=diff_text)
    mock_requests.get.return_value = mock_resp
    result = github_helper.get_pr_diff(42)
    assert "diff --git" in result
    assert "print('hello')" in result


@patch("github_helper.requests")
def test_get_pr_diff_not_found(mock_requests):
    mock_requests.get.return_value = _mock_response(
        ok=False, status_code=404, text="Not Found"
    )
    with pytest.raises(GitHubError) as exc_info:
        github_helper.get_pr_diff(999)
    assert exc_info.value.status_code == 404
    assert exc_info.value.context["pr_number"] == 999


# ---- get_pr_files ----
@patch("github_helper.requests")
def test_get_pr_files_happy(mock_requests):
    mock_requests.get.return_value = _mock_response(
        ok=True, status_code=200,
        json_data=[
            {
                "filename": "src/app/login.py",
                "status": "added",
                "additions": 30,
                "deletions": 0,
                "patch": "@@ -0,0 +1,30 @@\n+def login():\n+    pass",
            },
            {
                "filename": "tests/test_login.py",
                "status": "added",
                "additions": 15,
                "deletions": 0,
                "patch": "@@ -0,0 +1,15 @@\n+def test_login():\n+    pass",
            },
        ],
    )
    result = github_helper.get_pr_files(42)
    assert len(result) == 2
    assert result[0]["filename"] == "src/app/login.py"
    assert result[0]["status"] == "added"
    assert result[0]["additions"] == 30
    assert "patch" in result[0]


@patch("github_helper.requests")
def test_get_pr_files_http_error(mock_requests):
    mock_requests.get.return_value = _mock_response(
        ok=False, status_code=500, text="oops"
    )
    with pytest.raises(GitHubError) as exc_info:
        github_helper.get_pr_files(42)
    assert exc_info.value.status_code == 500
    assert exc_info.value.context["pr_number"] == 42


# ---- close_pr ----
@patch("github_helper.log")
@patch("github_helper.requests")
def test_close_pr_happy(mock_requests, mock_log):
    # Primeiro POST (comment), depois PATCH (close)
    mock_requests.post.return_value = _mock_response(ok=True, status_code=201)
    mock_requests.patch.return_value = _mock_response(ok=True, status_code=200)
    result = github_helper.close_pr(42, "Hard violation: print() em src/")
    assert result is True
    # Confirma chamadas: 1 post (comment) + 1 patch (close)
    assert mock_requests.post.call_count == 1
    assert mock_requests.patch.call_count == 1


@patch("github_helper.log")
@patch("github_helper.requests")
def test_close_pr_comment_fails(mock_requests, mock_log):
    mock_requests.post.return_value = _mock_response(
        ok=False, status_code=403, text="Forbidden"
    )
    with pytest.raises(GitHubError) as exc_info:
        github_helper.close_pr(42, "reason")
    assert exc_info.value.status_code == 403
    assert "close_pr.comment" in exc_info.value.context["operation"]
    # Patch nao deve ter sido chamado se comment falhou
    assert mock_requests.patch.call_count == 0


@patch("github_helper.log")
@patch("github_helper.requests")
def test_close_pr_patch_fails(mock_requests, mock_log):
    mock_requests.post.return_value = _mock_response(ok=True, status_code=201)
    mock_requests.patch.return_value = _mock_response(
        ok=False, status_code=422, text="Unprocessable"
    )
    with pytest.raises(GitHubError) as exc_info:
        github_helper.close_pr(42, "reason")
    assert exc_info.value.status_code == 422
    assert "close_pr.patch" in exc_info.value.context["operation"]


# ---- comment_pr_review ----
@patch("github_helper.log")
@patch("github_helper.requests")
def test_comment_pr_review_approve(mock_requests, mock_log):
    mock_requests.post.return_value = _mock_response(
        ok=True, status_code=200, json_data={"id": 12345}
    )
    result = github_helper.comment_pr_review(42, "APPROVE", "LGTM")
    assert result == 12345


@patch("github_helper.log")
@patch("github_helper.requests")
def test_comment_pr_review_request_changes(mock_requests, mock_log):
    mock_requests.post.return_value = _mock_response(
        ok=True, status_code=200, json_data={"id": 67890}
    )
    result = github_helper.comment_pr_review(42, "REQUEST_CHANGES", "Coverage abaixo de 80%")
    assert result == 67890


def test_comment_pr_review_invalid_event():
    """Event invalido nao deve fazer HTTP call - levanta antes."""
    with pytest.raises(GitHubError) as exc_info:
        github_helper.comment_pr_review(42, "MERGE_NOW", "body")
    assert "Invalid review event" in str(exc_info.value)
    assert exc_info.value.context["event"] == "MERGE_NOW"


@patch("github_helper.log")
@patch("github_helper.requests")
def test_comment_pr_review_http_error(mock_requests, mock_log):
    mock_requests.post.return_value = _mock_response(
        ok=False, status_code=422, text="Cannot approve own PR"
    )
    with pytest.raises(GitHubError) as exc_info:
        github_helper.comment_pr_review(42, "APPROVE", "body")
    assert exc_info.value.status_code == 422
    assert exc_info.value.context["event"] == "APPROVE"
