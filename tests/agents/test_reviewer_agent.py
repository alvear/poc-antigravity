"""
Testes do ReviewerAgent.

Cobertura:
- 5 hard violations (cada uma gera REJECT)
- 2 soft violations (geram REQUEST_CHANGES)
- Happy path (APPROVE)
- Hard > soft precedence
- Arquivos nao-python sao ignorados
- Shim CLI (exit codes)
"""

from unittest.mock import patch, MagicMock

import pytest

from agents.reviewer import ReviewerAgent
from agents.exceptions import GateRejected


# ============================================================
# Helpers
# ============================================================

def _file(filename, status="added", patch="", additions=0):
    return {
        "filename": filename,
        "status": status,
        "additions": additions,
        "deletions": 0,
        "patch": patch,
    }


# ============================================================
# Hard violations - cada uma deve gerar REJECT
# ============================================================

@patch("agents.reviewer.github_helper")
@patch("agents.base.gate_logger")
@patch("agents.base.log")
def test_reject_env_committed(mock_log, mock_gate, mock_gh):
    mock_gate.start_proposal.return_value = 999
    mock_gh.get_pr_files.return_value = [_file(".env", patch="+DB_PASS=x")]
    mock_gh.get_pr_diff.return_value = ""

    with pytest.raises(GateRejected) as exc_info:
        ReviewerAgent().run(42)

    assert exc_info.value.context["verdict"] == "REJECT"
    types = {v["type"] for v in exc_info.value.context["violations"]}
    assert "env_committed" in types
    mock_gh.close_pr.assert_called_once()


@patch("agents.reviewer.github_helper")
@patch("agents.base.gate_logger")
@patch("agents.base.log")
def test_reject_hardcoded_credential(mock_log, mock_gate, mock_gh):
    mock_gate.start_proposal.return_value = 999
    mock_gh.get_pr_files.return_value = [_file("src/config.py", patch="+token = x")]
    mock_gh.get_pr_diff.return_value = "+github_pat_" + "a" * 82

    with pytest.raises(GateRejected) as exc_info:
        ReviewerAgent().run(42)

    types = {v["type"] for v in exc_info.value.context["violations"]}
    assert "hardcoded_credential" in types


@patch("agents.reviewer.github_helper")
@patch("agents.base.gate_logger")
@patch("agents.base.log")
def test_reject_forbidden_import(mock_log, mock_gate, mock_gh):
    mock_gate.start_proposal.return_value = 999
    mock_gh.get_pr_files.return_value = [
        _file("src/app.py", patch="+from flask import Flask\n+def run_it(app):\n+    app.run()")
    ]
    mock_gh.get_pr_diff.return_value = ""

    with pytest.raises(GateRejected) as exc_info:
        ReviewerAgent().run(42)

    types = {v["type"] for v in exc_info.value.context["violations"]}
    assert "forbidden_import" in types


@patch("agents.reviewer.github_helper")
@patch("agents.base.gate_logger")
@patch("agents.base.log")
def test_reject_print_in_production(mock_log, mock_gate, mock_gh):
    mock_gate.start_proposal.return_value = 999
    mock_gh.get_pr_files.return_value = [
        _file("src/handler.py", patch="+def handle(req: dict) -> None:\n+    print(req)")
    ]
    mock_gh.get_pr_diff.return_value = ""

    with pytest.raises(GateRejected) as exc_info:
        ReviewerAgent().run(42)

    types = {v["type"] for v in exc_info.value.context["violations"]}
    assert "print_in_production" in types


@patch("agents.reviewer.github_helper")
@patch("agents.base.gate_logger")
@patch("agents.base.log")
def test_reject_missing_type_hints(mock_log, mock_gate, mock_gh):
    mock_gate.start_proposal.return_value = 999
    mock_gh.get_pr_files.return_value = [
        _file("src/util.py", patch="+def bad(a, b):\n+    return a + b")
    ]
    mock_gh.get_pr_diff.return_value = ""

    with pytest.raises(GateRejected) as exc_info:
        ReviewerAgent().run(42)

    types = {v["type"] for v in exc_info.value.context["violations"]}
    assert "missing_type_hints" in types


# ============================================================
# Soft violations - REQUEST_CHANGES
# ============================================================

@patch("agents.reviewer.github_helper")
@patch("agents.base.gate_logger")
@patch("agents.base.log")
def test_request_changes_missing_test(mock_log, mock_gate, mock_gh):
    mock_gate.start_proposal.return_value = 999
    mock_gh.get_pr_files.return_value = [
        _file(
            "src/new_mod.py",
            status="added",
            patch='+def helper(x: int) -> int:\n+    """Adds one."""\n+    return x + 1',
        )
    ]
    mock_gh.get_pr_diff.return_value = ""

    with pytest.raises(GateRejected) as exc_info:
        ReviewerAgent().run(42)

    assert exc_info.value.context["verdict"] == "REQUEST_CHANGES"
    types = {v["type"] for v in exc_info.value.context["violations"]}
    assert "missing_test" in types
    # Confirma que chamou review (nao close)
    mock_gh.comment_pr_review.assert_called_once()
    args = mock_gh.comment_pr_review.call_args
    assert args[0][1] == "REQUEST_CHANGES"


@patch("agents.reviewer.github_helper")
@patch("agents.base.gate_logger")
@patch("agents.base.log")
def test_request_changes_missing_docstring(mock_log, mock_gate, mock_gh):
    mock_gate.start_proposal.return_value = 999
    # Arquivo modificado (nao novo) com funcao sem docstring
    mock_gh.get_pr_files.return_value = [
        _file(
            "agents/something.py",
            status="modified",
            patch="+def do_it(x: int) -> int:\n+    return x + 1",
        )
    ]
    mock_gh.get_pr_diff.return_value = ""

    with pytest.raises(GateRejected) as exc_info:
        ReviewerAgent().run(42)

    assert exc_info.value.context["verdict"] == "REQUEST_CHANGES"
    types = {v["type"] for v in exc_info.value.context["violations"]}
    assert "missing_docstring" in types


# ============================================================
# Happy path - APPROVE
# ============================================================

@patch("agents.reviewer.github_helper")
@patch("agents.base.gate_logger")
@patch("agents.base.log")
def test_approve_clean_pr(mock_log, mock_gate, mock_gh):
    mock_gate.start_proposal.return_value = 999
    # PR modificado (nao added) + funcao com docstring + type hints + sem issues
    mock_gh.get_pr_files.return_value = [
        _file(
            "agents/clean.py",
            status="modified",
            patch='+def ok(x: int) -> int:\n+    """Documented."""\n+    return x',
        )
    ]
    mock_gh.get_pr_diff.return_value = ""

    result = ReviewerAgent().run(42)
    assert result["verdict"] == "APPROVE"
    assert result["files_reviewed"] == 1
    mock_gh.comment_pr_review.assert_called_once()
    args = mock_gh.comment_pr_review.call_args
    assert args[0][1] == "APPROVE"


# ============================================================
# Precedence: hard > soft
# ============================================================

@patch("agents.reviewer.github_helper")
@patch("agents.base.gate_logger")
@patch("agents.base.log")
def test_hard_takes_precedence_over_soft(mock_log, mock_gate, mock_gh):
    """Se tem hard E soft, PR vai REJECT, nao REQUEST_CHANGES."""
    mock_gate.start_proposal.return_value = 999
    # Arquivo novo em src/ sem teste (soft) + print() (hard)
    mock_gh.get_pr_files.return_value = [
        _file("src/mix.py", status="added", patch="+def bad(x: int) -> int:\n+    print(x)\n+    return x"),
    ]
    mock_gh.get_pr_diff.return_value = ""

    with pytest.raises(GateRejected) as exc_info:
        ReviewerAgent().run(42)

    # Deve ser REJECT (hard ganha), nao REQUEST_CHANGES
    assert exc_info.value.context["verdict"] == "REJECT"
    # close_pr foi chamado (REJECT action), comment_pr_review NAO
    mock_gh.close_pr.assert_called_once()
    mock_gh.comment_pr_review.assert_not_called()


# ============================================================
# Non-Python files ignored
# ============================================================

@patch("agents.reviewer.github_helper")
@patch("agents.base.gate_logger")
@patch("agents.base.log")
def test_non_python_files_ignored(mock_log, mock_gate, mock_gh):
    """Arquivos .md, .yml, etc. nao sao checados (so .env eh hard)."""
    mock_gate.start_proposal.return_value = 999
    mock_gh.get_pr_files.return_value = [
        _file("README.md", status="modified", patch="+# Print this output"),
        _file("docs/guide.md", status="added", patch="+import flask equivalent"),
    ]
    mock_gh.get_pr_diff.return_value = ""

    result = ReviewerAgent().run(42)
    assert result["verdict"] == "APPROVE"


# ============================================================
# Shim CLI
# ============================================================

def test_shim_exit_code_on_approve():
    """Shim retorna 0 quando ReviewerAgent aprova."""
    import reviewer_agent
    with patch.object(reviewer_agent, "ReviewerAgent") as mock_cls:
        instance = MagicMock()
        instance.execute.return_value = {"pr_number": 42, "files_reviewed": 3, "verdict": "APPROVE"}
        mock_cls.return_value = instance

        with patch.object(reviewer_agent.sys, "argv", ["reviewer_agent.py", "42"]):
            with patch.object(reviewer_agent.sys, "stdout"):
                rc = reviewer_agent.main()
        assert rc == 0


def test_shim_exit_code_on_reject():
    """Shim retorna 1 quando ReviewerAgent rejeita."""
    import reviewer_agent
    with patch.object(reviewer_agent, "ReviewerAgent") as mock_cls:
        instance = MagicMock()
        instance.execute.side_effect = GateRejected(
            "reviewer-agent",
            "PR #42 rejected",
            context={"pr_number": 42, "verdict": "REJECT", "violations": [
                {"type": "env_committed", "message": "bad"}
            ]},
        )
        mock_cls.return_value = instance

        with patch.object(reviewer_agent.sys, "argv", ["reviewer_agent.py", "42"]):
            with patch.object(reviewer_agent.sys, "stdout"):
                rc = reviewer_agent.main()
        assert rc == 1


def test_shim_exit_code_on_bad_args():
    """Shim retorna 2 quando argumento invalido."""
    import reviewer_agent

    with patch.object(reviewer_agent.sys, "argv", ["reviewer_agent.py"]):
        with patch.object(reviewer_agent.sys, "stderr"):
            rc = reviewer_agent.main()
    assert rc == 2
