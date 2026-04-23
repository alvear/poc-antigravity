# TECH_STACK.md

## Proposito deste arquivo

Contrato tecnico do servico construido neste repositorio. Define a stack usada, as regras de conformidade que os agentes devem verificar, e o que e proibido.

Os agentes da esteira Antigravity leem este arquivo antes de gerar ou revisar codigo, arquitetura, testes ou configuracao de infraestrutura.

Cada repositorio tem o seu proprio TECH_STACK.md. Se este repo for clonado como template, este arquivo deve ser reescrito refletindo a nova stack.

## Stack

### Runtime da aplicacao
- Python 3.12
- FastAPI 0.115+
- uvicorn[standard]
- Pydantic v2 (quando aplicavel)
- python-dotenv (apenas em desenvolvimento local)

### Scripts de automacao e agentes
Os scripts da esteira (helpers e agentes) usam bibliotecas mais pragmaticas que o codigo de aplicacao:
- requests (cliente HTTP sincrono)
- PyYAML (parsing de config)
- pytest + pytest-cov (testes unitarios)

### Infraestrutura
- Google Cloud Platform
- Cloud Run (runtime serverless da aplicacao e do gmud-bridge)
- Artifact Registry (registry de imagens Docker)
- Cloud Build (build de imagens com service account dedicada)
- Secret Manager (segredos de runtime)
- Workload Identity Federation (autenticacao GitHub Actions -> GCP, zero chaves estaticas)

### CI/CD
- GitHub Actions (pipeline unica aceita)
- GitHub Environments + Deployment Protection Rules (gates DEV/UAT/PRD)
- Branching: feature/* para desenvolvimento, main protegida, tags v* para releases

### Governanca de mudancas
- Jira Service Management (GMUD seguindo workflow ITIL)
- gmud-bridge (Cloud Run) traduz aprovacao JSM em liberacao no GitHub Environment
- Classificacao ITIL determinada na invocacao do Release Agent:
  - Standard Change (risk=LOW): pre-aprovado, auto-transiciona para IMPLEMENTING
  - Normal Change (risk=MEDIUM/HIGH): aguarda aprovacao do CAB em REVISAR

### Qualidade e seguranca
- SonarCloud (analise estatica multi-linguagem + cobertura)
- Bandit (SAST Python)
- Safety (SCA de dependencias Python)
- Checkov (analise de IaC)
- Trivy (scan de vulnerabilidades em imagens Docker)
- pytest + pytest-cov (testes unitarios com relatorio JUnit XML + Cobertura XML)
- Coverage minimo bloqueante: 80%

### Observabilidade
- Grafana Cloud (Loki) para logs estruturados
- Formato de log obrigatorio: JSON com campos `level`, `agent`, `message`, `service`, `ts`

### Documentacao
- Atlassian Confluence (space POCAntigra)
  - ADRs (Architecture Decision Records)
  - QA Evidence por historia
  - Release Notes por release
- README.md na raiz do repositorio

## Compliance Rules

Regras que os agentes (Architect, Developer, QA, Reviewer, Release) devem verificar antes de propor ou aprovar mudancas.

### Obrigatorio
- workload_identity_federation para autenticar GitHub Actions em GCP
- secret_manager para todo segredo em runtime
- structured_logging em formato JSON via grafana_logger
- health_endpoint: todo servico expoe `GET /health` retornando status ok
- conventional_commits: prefixos feat:, fix:, docs:, test:, chore:, ci:, refactor:
- type_hints em assinaturas de funcoes publicas
- docstrings em funcoes publicas
- tests_before_merge: pytest passando no CI antes de qualquer merge em main
- trivy_scan: imagens Docker sem CVEs CRITICAL ou HIGH antes de deploy
- coverage_80: cobertura de testes minima de 80%

### Proibido
- static_service_account_keys (chaves JSON de service account)
- hardcoded_secrets em codigo ou arquivos versionados
- docker_hub como registry (usar Artifact Registry)
- flask, django, starlette direto (usar FastAPI)
- print() em codigo de producao (usar grafana_logger)
- credenciais em arquivos versionados (.env nunca commitado)
- bibliotecas nao listadas na stack sem aprovacao previa

## Versionamento deste arquivo

Atualize este arquivo quando:
- Uma nova tecnologia for adicionada ou removida da stack
- Uma regra de conformidade for criada ou relaxada
- O nivel de cobertura minima mudar

Commits que modificam este arquivo devem usar prefixo `docs(stack):`
