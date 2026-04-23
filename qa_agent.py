"""
Compat shim: redireciona para agents.qa.

Mantem `python qa_agent.py ...` funcionando apos a migracao do Sprint 3.
Novo padrao: `python -m agents.qa ...`.
"""
import sys

from agents.qa import QAAgent

AGENT = QAAgent.AGENT_NAME


def run():
    """Wrapper legado (sem parametros, usa defaults como antes)."""
    return QAAgent().run()


if __name__ == "__main__":
    branch = sys.argv[1] if len(sys.argv) > 1 else "feature/POC-2-autenticacao-google-oauth"
    story = sys.argv[2] if len(sys.argv) > 2 else "POC-2"
    try:
        QAAgent().run(branch=branch, story=story)
    except Exception as exc:
        print(f"[QA] falhou: {exc}")
        sys.exit(1)