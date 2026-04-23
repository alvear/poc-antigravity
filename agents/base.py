"""
BaseAgent - classe base para todos os agentes da esteira Antigravity.

Fornece:
- Logging estruturado no Grafana com AGENT_NAME automatico
- Gate logger integrado via context manager `propose()`
- Tratamento de erros padronizado (falha = rejected no gate)
- Hooks opcionais on_start / on_finish / on_error para subclasses

Agentes concretos herdam e implementam `run()`.

Uso minimo:
    class MyAgent(BaseAgent):
        AGENT_NAME = "my-agent"
        
        def run(self, param):
            with self.propose("action-type", f"Fazendo {param}") as session:
                self.log_info(f"Trabalhando em {param}")
                # ... trabalho ...
                session.set_jira_key("POC-X")
            # Saiu sem excecao -> gate marca approved automaticamente
            # Saiu com excecao -> gate marca rejected automaticamente

Uso com hooks:
    class MyAgent(BaseAgent):
        AGENT_NAME = "my-agent"
        
        def on_start(self):
            self.log_info("Inicializando...")
        
        def on_finish(self, result):
            self.log_info(f"Terminei com resultado: {result}")
        
        def on_error(self, exc):
            self.log_error(f"Ops: {exc}")
        
        def run(self, param):
            self.on_start()
            try:
                result = self._do_work(param)
                self.on_finish(result)
                return result
            except Exception as e:
                self.on_error(e)
                raise
"""
from abc import ABC, abstractmethod
from contextlib import contextmanager

import grafana_logger as log
import gate_logger


class _GateSession:
    """Handle da sessao de gate para o context manager propose()."""
    
    def __init__(self, session_id: str):
        self.session_id = session_id
        self.jira_key = None
        self.extra = {}
    
    def set_jira_key(self, key: str):
        self.jira_key = key
    
    def add_context(self, **kwargs):
        """Adiciona contexto extra que sera passado ao record_decision."""
        self.extra.update(kwargs)


class BaseAgent(ABC):
    """Classe base. Subclasse define AGENT_NAME e implementa run()."""
    
    AGENT_NAME: str = ""  # subclasse DEVE definir: "pm-agent", "release-agent", etc
    
    def __init__(self):
        if not self.AGENT_NAME:
            raise ValueError(
                f"{type(self).__name__} precisa definir AGENT_NAME (class attribute)"
            )
    
    # ------------------------------------------------------------
    # Logging - proxy pro grafana_logger com AGENT_NAME automatico
    # ------------------------------------------------------------
    def log_info(self, message: str, extra: dict = None):
        log.info(self.AGENT_NAME, message, extra)
    
    def log_warn(self, message: str, extra: dict = None):
        log.warn(self.AGENT_NAME, message, extra)
    
    def log_error(self, message: str, extra: dict = None):
        log.error(self.AGENT_NAME, message, extra)
    
    def log_success(self, message: str, extra: dict = None):
        log.success(self.AGENT_NAME, message, extra)
    
    # ------------------------------------------------------------
    # Gate logger - context manager que automatiza propose/record
    # ------------------------------------------------------------
    @contextmanager
    def propose(self, proposal_type: str, summary: str):
        """
        Context manager para uma proposta do agente.
        
        Abre session_id no gate_logger, e ao sair do `with`:
        - Sem excecao   -> record_decision(approved)
        - Com excecao   -> record_decision(rejected, feedback=str(excecao))
        
        Yield um _GateSession que permite:
            session.set_jira_key("POC-X")
            session.add_context(foo="bar")
        """
        session_id = gate_logger.start_proposal(
            self.AGENT_NAME, proposal_type, summary
        )
        self.log_info(
            f"Proposta aberta: {proposal_type} - {summary}",
            {"session_id": session_id},
        )
        
        session = _GateSession(session_id)
        try:
            yield session
        except Exception as e:
            # Rejected path
            gate_logger.record_decision(
                session_id,
                "rejected",
                feedback=str(e),
                jira_key=session.jira_key,
            )
            self.log_error(
                f"Proposta rejeitada: {e}",
                {"session_id": session_id, "error": str(e), **session.extra},
            )
            raise
        else:
            # Approved path
            gate_logger.record_decision(
                session_id,
                "approved",
                jira_key=session.jira_key,
            )
            self.log_success(
                f"Proposta aprovada: {summary}",
                {"session_id": session_id, "jira_key": session.jira_key, **session.extra},
            )
    
    # ------------------------------------------------------------
    # Hooks - subclasses podem sobrescrever
    # ------------------------------------------------------------
    def on_start(self):
        """Chamado antes de run(). Override opcional pra setup."""
        self.log_info(f"Agent {self.AGENT_NAME} starting")
    
    def on_finish(self, result=None):
        """Chamado apos run() sem excecao. Override opcional."""
        self.log_info(f"Agent {self.AGENT_NAME} finished")
    
    def on_error(self, exc: Exception):
        """Chamado se run() levantar excecao. Override opcional."""
        self.log_error(f"Agent {self.AGENT_NAME} failed: {exc}")
    
    # ------------------------------------------------------------
    # Execucao - subclasse implementa run(), wrapper cuida dos hooks
    # ------------------------------------------------------------
    def execute(self, *args, **kwargs):
        """
        Executa run() com hooks automaticos.
        Chame isto no lugar de run() diretamente para ganhar os hooks.
        """
        self.on_start()
        try:
            result = self.run(*args, **kwargs)
            self.on_finish(result)
            return result
        except Exception as e:
            self.on_error(e)
            raise
    
    @abstractmethod
    def run(self, *args, **kwargs):
        """Subclasse implementa o fluxo do agente."""
