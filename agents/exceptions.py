"""
Hierarquia de excecoes da esteira Antigravity.

Estrategia:
- AntigravityError e a raiz de tudo
- HelperError abrange falhas de infra (API externa, IO, rede)
- AgentError abrange falhas logicas do agente (validacao, decisao)

Captura tipada e fortemente encorajada. Evitar `except Exception` generico.
"""


class AntigravityError(Exception):
    """Classe base de todas as excecoes da esteira."""


# ============================================================
# Infra errors - falhas em chamadas externas
# ============================================================
class HelperError(AntigravityError):
    """
    Erro generico em um helper (API externa, IO, rede).
    
    Atributos:
        helper: nome do helper que falhou ("jira", "github", "grafana", ...)
        message: descricao legivel da falha
        status_code: HTTP status code (se aplicavel)
        context: dict com metadados adicionais (endpoint, payload, etc)
    """
    
    def __init__(self, helper: str, message: str, status_code=None, context=None):
        self.helper = helper
        self.status_code = status_code
        self.context = context or {}
        suffix = f" (HTTP {status_code})" if status_code else ""
        super().__init__(f"[{helper}] {message}{suffix}")


class JiraError(HelperError):
    """Falha em chamada ao Jira Software REST API."""
    def __init__(self, message, status_code=None, context=None):
        super().__init__("jira", message, status_code, context)


class JSMError(HelperError):
    """Falha em chamada ao Jira Service Management REST API."""
    def __init__(self, message, status_code=None, context=None):
        super().__init__("jsm", message, status_code, context)


class ConfluenceError(HelperError):
    """Falha em chamada ao Confluence REST API."""
    def __init__(self, message, status_code=None, context=None):
        super().__init__("confluence", message, status_code, context)


class GitHubError(HelperError):
    """Falha em chamada ao GitHub REST API."""
    def __init__(self, message, status_code=None, context=None):
        super().__init__("github", message, status_code, context)


class GrafanaError(HelperError):
    """Falha em envio de log para Grafana Loki."""
    def __init__(self, message, status_code=None, context=None):
        super().__init__("grafana", message, status_code, context)


class ArchiError(HelperError):
    """Falha em geracao ou manipulacao de modelos ArchiMate."""
    def __init__(self, message, context=None):
        super().__init__("archi", message, None, context)


# ============================================================
# Agent errors - falhas logicas do agente
# ============================================================
class AgentError(AntigravityError):
    """
    Erro logico dentro de um agente (nao e falha de infra).
    
    Atributos:
        agent: nome do agente ("release-agent", "qa-agent", ...)
        message: descricao legivel
        context: dict com metadados
    """
    
    def __init__(self, agent: str, message: str, context=None):
        self.agent = agent
        self.context = context or {}
        super().__init__(f"[{agent}] {message}")


class ValidationError(AgentError):
    """Input ou estado invalido. Nao se torna valido com retry."""


class GateRejected(AgentError):
    """Decisao de gate foi rejeitada. E um fluxo esperado, nao um bug."""


class ReleaseStageFailure(AgentError):
    """Pipeline stage (Bake, DEV, UAT, PRD) falhou ou deu timeout."""
