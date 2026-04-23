# POC Antigravity - Estado Atual

> **Documento consolidado para project knowledge.** Substitui historicos anteriores.
> Ultima atualizacao: 24/04/2026 (apos Bloco C Parte 1).

---

## Quem somos

**Alvear** - Hyperautomation Coordinator no Banco BV.
**POC Antigravity** - simula SDLC end-to-end com agentes IA, governanca ITIL, em GCP.
**Proposito atual:** Piloto real (Proposito C). Sem prazo definido.

---

## Stack consolidada

| Item | Valor |
|---|---|
| Linguagem | Python 3.12 (CI) / 3.13 (local) |
| Framework | FastAPI 0.135.1 |
| Cloud | GCP project alvear-456111 (project_number 885731178849), region us-central1 |
| Repo | github.com/alvear/poc-antigravity (PUBLICO, branch main) |
| Atlassian DUAL SITE | sprandelalvear.atlassian.net (Jira POC + Confluence POCAntigra) e sprandel.atlassian.net (JSM GMUD) |
| Observability | Grafana Cloud (logs-prod-024.grafana.net, user 1553357) |
| Quality | SonarCloud (org alvear, project alvear_poc-antigravity) |
| Path local | C:\\Users\\spran\\poc-antigravity (Windows PowerShell) |
| Editor | Antigravity (VS Code-like) |

### Configuracao critica

.env local com 13 variaveis (sem BOM):
JIRA_URL/EMAIL/TOKEN/PROJECT, JSM_URL/PROJECT, CONFLUENCE_SPACE,
GITHUB_OWNER/REPO/TOKEN, GRAFANA_LOKI_URL/USER/TOKEN.

2 vars runtime (Cloud Run, nao no .env): VERSION, WEBHOOK_SECRET.

**Tokens expostos no chat anterior** (GitHub, Jira, Grafana). Usuario RECUSOU rotacao.
Documentado em docs/SECRETS.md.

---

## Estado dos sprints (24/04/2026)

[x] Sprint 1 - Consolidacao (PRODUCT_SPEC, TECH_STACK, rules.md)
[x] Sprint 2 - Configuracao central (config.py com Settings + SecretStr)
[x] Sprint 3 - Classe base BaseAgent + agents/ + shims raiz
[x] Sprint 4 - Error handling padronizado (hierarquia exceptions, 11 tipos)
[x] Sprint 5 - Testes dos proprios agentes (110 testes)
[x] Bloco C Parte 1 - github_helper estendido para Reviewer (124 testes)

PROXIMOS (em ordem):
[ ] Bloco C Parte 2 - agents/reviewer.py + shim          (~1h)
[ ] Bloco D - QA Agent v2 (geracao em 3 tipos)           (~2-3h sessao dedicada)
[ ] Bloco G - SI Agent 3 camadas                         (~8-11h sessao dedicada)
[ ] Sprint 6 - ADRs documentando decisoes                (~1h)
[ ] Sprint 7 - CI/CD do codigo dos agentes               (~45min)
[ ] Bloco F - Release v2.0.0 end-to-end                  (~30min)

### Metricas atuais

| Metrica | Valor |
|---|---|
| Testes totais | 124 |
| Coverage src/ | 100% |
| CI gates verdes | 6/6 (Run #70) |
| Modulos com testes | 12 |
| Tipos de excecao | 11 |
| Agentes implementados | 2 (Release, QA) + BaseAgent |

---

## Arquitetura

### Estrutura de diretorios

poc-antigravity/
  src/                           # Aplicacao FastAPI (cobertura 100%)
    main.py                      # OAuth2 Google
    app/routers/auth.py
  agents/                        # Agentes (BaseAgent + concretos)
    __init__.py
    base.py                      # BaseAgent + propose() context manager
    exceptions.py                # Hierarquia de excecoes (11 tipos)
    release.py                   # ReleaseAgent
    qa.py                        # QAAgent
    qa_templates.py              # Templates de teste
  tests/                         # 124 testes total
    test_auth.py                 (11)
    test_jira_helper.py          (9)
    test_jsm_helper.py           (9)
    test_github_helper.py        (24)   <- 14 novos no Bloco C P1
    test_confluence_helper.py    (6)
    test_grafana_logger.py       (8)
    test_archi_helper.py         (4)
    test_gate_logger.py          (7)
    agents/
      test_base.py               (10)
      test_exceptions.py         (23)
      test_release_agent.py      (9)
      test_qa_agent.py           (5)
  jira_helper.py                 # CRUD Jira
  jsm_helper.py                  # GMUD via JSM
  github_helper.py               # 10 funcoes: branches/commits/PRs/tags/reviews
  confluence_helper.py           # Paginas
  grafana_logger.py              # Logs (NUNCA levanta - stderr only)
  archi_helper.py                # ArchiMate XML
  gate_logger.py                 # FPY tracking (.gate_sessions.json)
  config.py                      # Settings central (pydantic-settings)
  release_agent.py               # SHIM -> agents/release.py
  qa_agent.py                    # SHIM -> agents/qa.py
  .env.example
  docs/SECRETS.md
  _archive/                      # Scripts temporarios + backups + resumos
  .antigravity/rules.md          # Rules dos 6 agentes
  PRODUCT_SPEC.md
  TECH_STACK.md
  requirements.txt
  .github/workflows/ci.yml       # 6 gates: Bandit/Safety/Checkov/Trivy/Sonar/Grafana

### Hierarquia de excecoes (Sprint 4)

AntigravityError (raiz)
  HelperError (helper, status_code, context)
    JiraError, JSMError, ConfluenceError, GitHubError, GrafanaError, ArchiError
  AgentError (agent, context)
    ValidationError, GateRejected, ReleaseStageFailure

### BaseAgent pattern (Sprint 3)

Todos os agentes herdam de BaseAgent:
- AGENT_NAME obrigatorio (class attribute)
- run() abstract method
- propose(proposal_type, summary) context manager - integra gate_logger automaticamente
- log_info/error/warn/success(message, context=None) - proxies para grafana_logger
- Hooks: on_start, on_finish, on_error

### github_helper.py - 10 funcoes (apos Bloco C P1)

Branches/commits/PRs (originais):
  get_branch_sha, create_branch, commit_file, create_pr, create_tag

PRs avancado (Bloco C P1):
  list_open_prs, get_pr_diff, get_pr_files, close_pr, comment_pr_review

Funcoes que existem inline em agents/release.py mas NAO no github_helper:
latest_run_for_workflow, get_run, get_pending_deployments, approve_deployment, get_run_jobs
(refatoracao opcional em Sprint 6/7)

---

## Padroes consolidados (CRITICAL para qualquer mudanca)

### 1. Mocks de testes

CORRETO: patch em modulo importado
  @patch("jira_helper.requests")
  @patch("jira_helper.log")
  def test_xxx(mock_requests, mock_log):
      mock_requests.post.return_value = _mock_response(ok=True, ...)

- @patch("<modulo>.<nome>") so funciona se <nome> esta no namespace de <modulo>
- log/gate_logger sao SEMPRE de agents.base (nao de release/qa)
- Helper _mock_response(ok, status_code, json_data, text) ja existe em cada test_*_helper.py
- time.time() em loops -> usar time.time_ns() para garantir unicidade
- Mocks de funcoes com loops devem mockar 'time' inteiro com side_effect, nao so time.sleep

### 2. Erros em helpers

CORRETO:
  if not r.ok:
      raise XxxError(
          f"Failed to <op>: {r.text[:200]}",
          status_code=r.status_code,
          context={"key": value, "operation": "<funcao>"},
      )

- ZERO raise_for_status() novo (todos foram migrados no Sprint 4)
- grafana_logger e EXCECAO: nunca levanta, escreve em stderr (servico de log nao pode quebrar app)

### 3. Decisoes arquiteturais firmes

| Decisao | Valor |
|---|---|
| Coverage | Bloqueante em 80% (--cov-fail-under=80) |
| Trivy | Bloqueante em CRITICAL/HIGH |
| Reviewer Agent | Hibrido B+C (REJECT/REQUEST_CHANGES/APPROVE), nunca mescla sozinho |
| Risk como parametro | do Release Agent, nao no PRODUCT_SPEC |
| Contexto descentralizado | cada repo tem seu PRODUCT_SPEC + TECH_STACK |
| SHA pinning de actions | trivy-action@57a97c7e... (supply chain) |
| Tokens expostos | rotacao adiada (decisao pragmatica do usuario) |

### 4. Conventional Commits

feat(<scope>): ...
fix(<scope>): ...
test(<scope>): ...
docs(<scope>): ...
chore(<scope>): ...

Scopes usados: github, jira, jsm, confluence, grafana, archi, gate, agents, config, ci, deploy.

---

## Bloco D - Design definido (para proxima sessao)

### Conceito central

O QAAgent atual e monolitico e hardcoded para o caso OAuth (POC-2). Tem 1 metodo publico
que gera um arquivo unico de testes via templates fixos.

**O que muda no Bloco D:** QAAgent aprende 3 modos de geracao distintos, cada um com
template proprio, para que quando rodar em aplicacoes novas, distribua os testes gerados
respeitando a piramide 70/20/10 definida no TECH_STACK.md do repositorio alvo.

### Escopo

1. Tres metodos de geracao na classe:
   - generate_unit(module, feature) - template com @patch/MagicMock, funcoes puras, happy+error paths
   - generate_integration(endpoint, feature) - template com TestClient/httpx.AsyncClient, fixtures, sem mock de rede
   - generate_e2e(user_story, feature) - template com @pytest.mark.e2e + Gherkin simplificado

2. run() recebe lista de cenarios e decide distribuicao entre os 3 tipos.

3. Gera 3 arquivos separados em tests/unit/, tests/integration/, tests/e2e/.

4. TECH_STACK.md do repositorio alvo declara a proporcao alvo (70/20/10 e default,
   mas configuravel por projeto).

### Esforco estimado

~2-3h em sessao dedicada. Praticamente refeitura do QAAgent - e a maior mudanca
arquitetural do pacote agents/ desde o BaseAgent no Sprint 3.

### Pre-requisitos

- Decidir formato de declaracao da piramide no TECH_STACK.md
- Definir se generate_e2e usa pytest-bdd ou scenarios em string simples
- Decidir se generate_integration usa testcontainers ou fixtures padrao

### Relacao com Bloco H (PRINCIPLES)

Bloco H define principios que os agentes aplicam no codigo gerado. Piramide de Testes e
um desses principios (Parte A). Idealmente, Bloco H acontece ANTES do Bloco D, porque
o Bloco H define COMO se caracteriza cada tipo de teste, e o Bloco D implementa a geracao
seguindo essas caracterizacoes.

### Lessons learned da tentativa de implementacao (24/04/2026)

Durante esta sessao tentamos implementar o Bloco D Parte 1 como "piramide como metrica de
auditoria" - QAAgent ganhava metodos classify_test_type + validate_pyramid que escaneavam
testes existentes. Isso foi revertido porque:

- Nao agrega valor a POC (testar a propria POC com piramide e irrelevante)
- Desvia do conceito central: principios devem ser aplicados pelos agentes quando eles
  GERAM codigo para aplicacoes novas, nao quando validam a POC propria
- A confusao foi de interpretacao - "piramide configuravel" pode significar auditoria
  ou geracao guiada, e a interpretacao correta e geracao

Esta licao motivou a separacao conceitual acima (pre-requisitos claros antes de implementar).

---

## Como retomar - PROXIMO PASSO

### Bloco C Parte 2 - Reviewer Agent (~1h)

Design ja decidido:
- Hibrido B+C: REJECT / REQUEST_CHANGES / APPROVE
- Nunca mescla sozinho - humano sempre faz merge final
- Disparo manual: python reviewer_agent.py [pr_number]

Hard violations (REJECT automatico):
- .env commitado no diff
- Credenciais hardcoded (regex tokens AWS/GCP/Jira/GitHub)
- Import de biblioteca proibida (flask, django)
- print() em codigo de producao (src/ ou agentes principais)
- Assinatura de funcao publica sem type hints

Soft violations (REQUEST_CHANGES):
- Falta de docstring em funcao publica
- Coverage no codigo novo abaixo de 80%
- Commit message fora do padrao Conventional Commits
- Arquivo novo em src/ sem teste correspondente em tests/
- Endpoint novo sem /health

Etapas previstas:
1. Criar agents/reviewer.py com ReviewerAgent(BaseAgent) (~40min)
2. Shim reviewer_agent.py na raiz (~5min)
3. Testes em tests/agents/test_reviewer_agent.py ~10 testes (~20min)
4. Atualizar .antigravity/rules.md com secao do Reviewer (~5min)
5. Pytest local + push + CI verde (~10min)

### Como abrir a proxima conversa

"Continuando POC Antigravity. Acabei de fechar Bloco C Parte 1.
Proximo passo: Bloco C Parte 2 - criar agents/reviewer.py."

Eu vou ler este documento + arquivos relevantes via search e estarei operacional em 1-2 turnos.

---

## Arquivos do _archive (referencia, nao precisa anexar)

- _archive/SESSAO_23_ABR_2026.md (sessao Sprints 1-5)
- _archive/SESSAO_24_ABR_2026.md (sessao Bloco C Parte 1)
- _archive/backup_pre_sprint{2,3,5}/ (backups por sprint)
- _archive/backup_pre_blocoC/ (backup antes do Bloco C)
