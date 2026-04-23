"""
Compat shim: redireciona para agents.release.

Mantem `python release_agent.py ...` funcionando apos a migracao do Sprint 3.
Novo padrao: `python -m agents.release ...`.
"""
import sys

from agents.release import ReleaseAgent

# Backward compat: exporta funcoes/valores que scripts antigos podiam importar.
AGENT = ReleaseAgent.AGENT_NAME


def run_release(release_tag, summary, jira_story_key=None,
                affected_envs="DEV,UAT,PRD", risk="LOW"):
    """Wrapper legado. Novo codigo deve usar ReleaseAgent().run() diretamente."""
    return ReleaseAgent().run(release_tag, summary, jira_story_key, affected_envs, risk)


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Uso: python release_agent.py <tag> <summary> [jira_story_key] [envs] [risk]")
        sys.exit(1)
    tag = sys.argv[1]
    summary = sys.argv[2]
    story = sys.argv[3] if len(sys.argv) > 3 else None
    envs = sys.argv[4] if len(sys.argv) > 4 else "DEV,UAT,PRD"
    risk = sys.argv[5] if len(sys.argv) > 5 else "LOW"
    try:
        ReleaseAgent().run(tag, summary, story, envs, risk)
    except Exception as exc:
        print(f"[RELEASE] falhou: {exc}")
        sys.exit(1)