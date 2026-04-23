"""
ReviewerAgent - valida PRs abertos pelo Developer Agent.

Design hibrido B+C:
- REJECT (hard violation): fecha o PR automaticamente
- REQUEST_CHANGES (soft violation): comenta sugestoes no PR
- APPROVE: marca review aprovada no GitHub

Restricao critica: o Reviewer NUNCA faz merge. O merge final e sempre humano.
"""

import re

import github_helper
from agents.base import BaseAgent
from agents.exceptions import GateRejected


# ============================================================
# Patterns de deteccao
# ============================================================

# Uso de chr(34)=" e chr(39)=' onde misturamos aspas evita escape problematico.
_DQ = chr(34)
_SQ = chr(39)

CREDENTIAL_PATTERNS = [
    (r"AKIA[0-9A-Z]{16}", "AWS Access Key"),
    (r"ghp_[A-Za-z0-9]{36,}", "GitHub Personal Access Token"),
    (r"ghs_[A-Za-z0-9]{36,}", "GitHub Server Token"),
    (r"github_pat_[A-Za-z0-9_]{82,}", "GitHub Fine-grained PAT"),
    (r"ATATT3x[A-Za-z0-9_\-]{100,}", "Atlassian API Token"),
    (r"-----BEGIN (RSA |OPENSSH |EC |DSA |PRIVATE)", "Private Key Block"),
]

FORBIDDEN_IMPORTS = [
    (r"^\s*(from|import)\s+flask\b", "flask"),
    (r"^\s*(from|import)\s+django\b", "django"),
]

PRINT_CALL = re.compile(r"^\s*(?!#).*\bprint\s*\(", re.MULTILINE)

FUNC_PUBLIC = re.compile(
    r"^def\s+(?!_)([a-zA-Z_][a-zA-Z0-9_]*)\s*\(([^)]*)\)(\s*->\s*[^:]+)?:",
    re.MULTILINE,
)

# Docstring detecta: def publica seguida por linha com tres aspas (simples ou duplas).
# Construimos com chr() para evitar escape de aspas no source.
_triple_dq = _DQ * 3
_triple_sq = _SQ * 3
_docstring_pattern = (
    r"^def\s+(?!_)([a-zA-Z_][a-zA-Z0-9_]*)\s*\([^)]*\)[^:]*:\s*\n\s*(?:"
    + re.escape(_triple_dq)
    + "|"
    + re.escape(_triple_sq)
    + ")"
)
DOCSTRING_AFTER_DEF = re.compile(_docstring_pattern, re.MULTILINE)


class ReviewerAgent(BaseAgent):
    """Agente hibrido B+C para revisao automatica de PRs."""

    AGENT_NAME = "reviewer-agent"

    def run(self, pr_number):
        """Revisa um PR e aplica veredicto (REJECT, REQUEST_CHANGES, APPROVE)."""
        pr_number = int(pr_number)

        with self.propose("pr_review", "PR #" + str(pr_number)):
            self.log_info("Iniciando review de PR #" + str(pr_number))

            pr_files = github_helper.get_pr_files(pr_number)
            pr_diff = github_helper.get_pr_diff(pr_number)

            hard = self._check_hard_violations(pr_files, pr_diff)
            if hard:
                body = self._format_reject_body(hard)
                github_helper.close_pr(pr_number, body)
                self.log_warn("PR #" + str(pr_number) + " rejeitado: " + str(len(hard)) + " hard violations")
                raise GateRejected(
                    self.AGENT_NAME,
                    "PR #" + str(pr_number) + " rejected: " + str(len(hard)) + " hard violations",
                    context={
                        "pr_number": pr_number,
                        "verdict": "REJECT",
                        "violations": hard,
                    },
                )

            soft = self._check_soft_violations(pr_files)
            if soft:
                body = self._format_request_changes_body(soft)
                github_helper.comment_pr_review(pr_number, "REQUEST_CHANGES", body)
                self.log_warn("PR #" + str(pr_number) + ": " + str(len(soft)) + " soft violations")
                raise GateRejected(
                    self.AGENT_NAME,
                    "PR #" + str(pr_number) + " requires changes: " + str(len(soft)) + " soft violations",
                    context={
                        "pr_number": pr_number,
                        "verdict": "REQUEST_CHANGES",
                        "violations": soft,
                    },
                )

            body = self._format_approve_body(pr_files)
            github_helper.comment_pr_review(pr_number, "APPROVE", body)
            self.log_success("PR #" + str(pr_number) + " aprovado pelo Reviewer")

            return {
                "pr_number": pr_number,
                "verdict": "APPROVE",
                "files_reviewed": len(pr_files),
            }

    def _check_hard_violations(self, pr_files, pr_diff):
        """Retorna lista de violacoes hard."""
        violations = []

        for f in pr_files:
            fname = f["filename"]
            if fname.endswith(".env") or fname == ".env":
                violations.append({
                    "type": "env_committed",
                    "file": fname,
                    "message": "Arquivo de ambiente commitado: " + fname,
                })

        for pattern, label in CREDENTIAL_PATTERNS:
            if re.search(pattern, pr_diff):
                violations.append({
                    "type": "hardcoded_credential",
                    "label": label,
                    "message": "Credencial hardcoded detectada: " + label,
                })

        for f in pr_files:
            fname = f["filename"]
            if not fname.endswith(".py"):
                continue
            if f["status"] == "removed":
                continue
            patch = f.get("patch") or ""
            if not patch:
                continue
            added_lines = "\n".join(
                line[1:] for line in patch.split("\n")
                if line.startswith("+") and not line.startswith("+++")
            )

            for pattern, lib in FORBIDDEN_IMPORTS:
                if re.search(pattern, added_lines, re.MULTILINE):
                    violations.append({
                        "type": "forbidden_import",
                        "file": fname,
                        "library": lib,
                        "message": "Import proibido (" + lib + ") em " + fname,
                    })

            in_production = fname.startswith("src/") or fname.startswith("agents/")
            if in_production and PRINT_CALL.search(added_lines):
                violations.append({
                    "type": "print_in_production",
                    "file": fname,
                    "message": "print() detectado em " + fname + " - use logger",
                })

            if in_production:
                for match in FUNC_PUBLIC.finditer(added_lines):
                    name = match.group(1)
                    params_raw = match.group(2).strip()
                    return_hint = match.group(3)
                    real_params = [
                        p.strip() for p in params_raw.split(",")
                        if p.strip() and p.strip() not in ("self", "cls")
                    ]
                    params_untyped = bool(real_params) and not any(":" in p for p in real_params)
                    missing_return = bool(real_params) and not return_hint
                    if params_untyped or missing_return:
                        violations.append({
                            "type": "missing_type_hints",
                            "file": fname,
                            "function": name,
                            "message": "Funcao publica " + name + "() sem type hints em " + fname,
                        })

        return violations

    def _check_soft_violations(self, pr_files):
        """Retorna lista de violacoes soft."""
        violations = []
        filenames = {f["filename"] for f in pr_files}

        for f in pr_files:
            fname = f["filename"]
            if not fname.endswith(".py"):
                continue
            if f["status"] == "removed":
                continue

            if (
                f["status"] == "added"
                and fname.startswith("src/")
                and not fname.endswith("__init__.py")
            ):
                stem = fname.replace("src/", "").replace("/", "_").replace(".py", "")
                basename = fname.split("/")[-1]
                expected_tests = {
                    "tests/test_" + stem + ".py",
                    "tests/test_" + basename,
                }
                has_test = any(t in filenames for t in expected_tests)
                if not has_test:
                    violations.append({
                        "type": "missing_test",
                        "file": fname,
                        "message": "Arquivo novo " + fname + " sem teste correspondente em tests/",
                    })

            patch = f.get("patch") or ""
            if not patch:
                continue
            added = "\n".join(
                line[1:] for line in patch.split("\n")
                if line.startswith("+") and not line.startswith("+++")
            )
            in_production = fname.startswith("src/") or fname.startswith("agents/")
            if not in_production:
                continue

            public_funcs = {m.group(1) for m in FUNC_PUBLIC.finditer(added)}
            with_docstring = {m.group(1) for m in DOCSTRING_AFTER_DEF.finditer(added)}
            missing_docstring = public_funcs - with_docstring
            for name in missing_docstring:
                violations.append({
                    "type": "missing_docstring",
                    "file": fname,
                    "function": name,
                    "message": "Funcao publica " + name + "() sem docstring em " + fname,
                })

        return violations

    def _format_reject_body(self, violations):
        """Body do comentario de REJECT."""
        lines = [
            "## Reviewer Agent - REJECT",
            "",
            "Este PR contem violacoes hard que bloqueiam o merge automaticamente:",
            "",
        ]
        for v in violations:
            lines.append("- **" + v["type"] + "**: " + v["message"])
        lines.append("")
        lines.append("Corrija os pontos acima e abra um novo PR.")
        return "\n".join(lines)

    def _format_request_changes_body(self, violations):
        """Body do comentario de REQUEST_CHANGES."""
        lines = [
            "## Reviewer Agent - REQUEST_CHANGES",
            "",
            "Este PR tem ajustes recomendados antes do merge:",
            "",
        ]
        for v in violations:
            lines.append("- **" + v["type"] + "**: " + v["message"])
        lines.append("")
        lines.append("Considere atender as sugestoes ou justifique nos comentarios.")
        lines.append("Merge final e humano.")
        return "\n".join(lines)

    def _format_approve_body(self, pr_files):
        """Body do comentario de APPROVE."""
        return (
            "## Reviewer Agent - APPROVE\n\n"
            + "Conformidade atendida ("
            + str(len(pr_files))
            + " arquivos revisados). "
            + "Merge final continua sendo humano."
        )
