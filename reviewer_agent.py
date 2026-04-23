"""
Shim backward-compat - redireciona para agents.reviewer.ReviewerAgent.

Uso:
    python reviewer_agent.py <pr_number>
"""

import sys

from agents.reviewer import ReviewerAgent
from agents.exceptions import GateRejected


def main():
    """Executa ReviewerAgent sobre um PR passado por CLI."""
    if len(sys.argv) < 2:
        sys.stderr.write("Uso: python reviewer_agent.py <pr_number>\n")
        return 2

    try:
        pr_number = int(sys.argv[1])
    except ValueError:
        sys.stderr.write("pr_number deve ser inteiro, recebido: " + sys.argv[1] + "\n")
        return 2

    try:
        result = ReviewerAgent().execute(pr_number)
        sys.stdout.write(
            "APPROVE: PR #"
            + str(result["pr_number"])
            + " ("
            + str(result["files_reviewed"])
            + " arquivos)\n"
        )
        return 0
    except GateRejected as e:
        verdict = e.context.get("verdict", "REJECTED")
        violations = e.context.get("violations", [])
        pr_number_ctx = e.context.get("pr_number", "?")
        sys.stdout.write(
            verdict + ": PR #" + str(pr_number_ctx)
            + " (" + str(len(violations)) + " violations)\n"
        )
        for v in violations:
            sys.stdout.write("  - " + v.get("type", "?") + ": " + v.get("message", "?") + "\n")
        return 1


if __name__ == "__main__":
    sys.exit(main())
