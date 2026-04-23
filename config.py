"""
Configuracao central da esteira Antigravity.

Todos os helpers e agentes devem importar daqui ao inves de usar
os.environ diretamente. Isso garante:

- Validacao das variaveis obrigatorias no boot (nao em runtime)
- Tipagem correta (SecretStr para tokens, nunca vazam em logs)
- Aliases convenientes (Confluence usa auth do Jira, etc)
- Reutilizavel: se a esteira rodar em outro projeto, basta trocar .env

Uso:
    from config import settings
    token = settings.jira_token.get_secret_value()
    url   = settings.jira_url
"""
from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Carregada uma unica vez no import. Falha no boot se faltar var obrigatoria."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    # ---- Atlassian Jira Software (backlog) ----
    jira_url: str
    jira_email: str
    jira_token: SecretStr
    jira_project: str

    # ---- Atlassian JSM (governanca de mudancas) ----
    # Em dual-site setup, JSM pode estar em tenant separado do Jira Software.
    jsm_url: str
    jsm_project: str

    # ---- Confluence ----
    # Compartilha auth do Jira (mesmo tenant Atlassian).
    confluence_space: str

    # ---- GitHub ----
    github_owner: str
    github_repo: str
    github_token: SecretStr

    # ---- Grafana Cloud (logs estruturados) ----
    grafana_loki_url: str
    grafana_user: str
    grafana_token: SecretStr

    # ---- Aliases: Confluence reusa credenciais do Jira ----
    @property
    def confluence_url(self) -> str:
        """Confluence roda no mesmo tenant Atlassian do Jira Software."""
        return self.jira_url

    @property
    def confluence_email(self) -> str:
        return self.jira_email

    @property
    def confluence_token(self) -> SecretStr:
        return self.jira_token


# Singleton carregado 1x no import.
# Falha no boot se faltar var obrigatoria (mensagem clara do Pydantic).
settings = Settings()


if __name__ == "__main__":
    # Exec direto: valida config e imprime mascarado (sem vazar tokens).
    print("Settings carregadas com sucesso.")
    print(f"  jira_url:          {settings.jira_url}")
    print(f"  jira_email:        {settings.jira_email}")
    print(f"  jira_token:        {settings.jira_token}")  # SecretStr mostra ****
    print(f"  jira_project:      {settings.jira_project}")
    print(f"  jsm_url:           {settings.jsm_url}")
    print(f"  jsm_project:       {settings.jsm_project}")
    print(f"  confluence_space:  {settings.confluence_space}")
    print(f"  github_owner:      {settings.github_owner}")
    print(f"  github_repo:       {settings.github_repo}")
    print(f"  github_token:      {settings.github_token}")
    print(f"  grafana_loki_url:  {settings.grafana_loki_url}")
    print(f"  grafana_user:      {settings.grafana_user}")
    print(f"  grafana_token:     {settings.grafana_token}")
