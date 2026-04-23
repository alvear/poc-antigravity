# POC Antigravity - SDLC End-to-End com IA

> ### [V1 PAUSADA] desde 24/04/2026
>
> **Esta e a V1 da POC, congelada em estado demonstravel.** O paradigma foi
> ressignificado para V2 (IDE-centric com Gemini embutido no Antigravity,
> like Devin). Ver [`docs/HANDOFF.md`](docs/HANDOFF.md) para detalhes do pivote.
>
> **O que esta em V1 e funciona:** stack GCP completa, 137 testes, 100% coverage,
> 6/6 gates CI verdes, 3 agentes Python autonomos (Release, QA, Reviewer),
> 27 padroes arquiteturais documentados (`.antigravity/agent_guidelines.md`),
> ambos os fluxos ITIL validados em producao.
>
> **Tag de marco:** `v1.0.0-paused`
>
> Estado consolidado: [`POC_ESTADO_ATUAL.md`](POC_ESTADO_ATUAL.md)

---

## Status original da V1

> **Status:** POC validada end-to-end, ambos os fluxos ITIL demonstrados em producao GCP.

## Objetivo

Demonstrar um ciclo completo de SDLC orquestrado por agentes IA, onde cada etapa (PM, Arquitetura, Desenvolvimento, QA, Release) e executada por um agente autonomo que dispara o proximo, com gates humanos no CAB conforme classificacao ITIL da mudanca.

## Stack

| Camada | Ferramenta |
|---|---|
| Linguagem | Python 3.12 + FastAPI |
| Pipelines CI/CD | GitHub Actions |
| Container Registry | GCP Artifact Registry |
| Runtime | Cloud Run |
| Autenticacao entre sistemas | Workload Identity Federation |
| Gestao de segredos | GCP Secret Manager |
| ITSM / Gestao de mudancas | Jira Service Management |
| Observabilidade | Grafana Cloud (Loki) |
| Documentacao | Atlassian Confluence |
| Backlog | Atlassian Jira Software |
| Qualidade de codigo | SonarCloud + Bandit + Safety + Checkov |

## Arquitetura - cadeia agentica

PM Agent (Jira) cria epicos e historias.
Architect Agent (Confluence + Archi) gera ADR e diagrama.
Developer Agent (GitHub) cria branch, codigo e PR.
QA Agent (pytest + Confluence) gera testes e evidencia.
Release Agent (tag + pipeline + GMUD + Release Notes) orquestra o deploy.
gmud-bridge (Cloud Run) recebe webhook do JSM e chama a GitHub Deployment API.
Deploy em Cloud Run PRD e automatizado apos aprovacao.

## Fluxos ITIL demonstrados

### Standard Change (risk=LOW)

Pre-aprovado no catalogo ITIL. Release Agent auto-transiciona GMUD para IMPLEMENTING diretamente. Zero intervencao humana.

Comando:

    python release_agent.py v1.2.0 "Hotfix pequeno" POC-2 "DEV,UAT,PRD" LOW

Tempo medido: 4m 34s (do push da tag ate versao ativa em producao).

### Normal Change (risk=MEDIUM ou HIGH)

Requer aprovacao do CAB. Release Agent auto-transiciona ate REVISAR e espera decisao humana. Apos aprovacao, bridge destrava deploy em PRD automaticamente.

Comando:

    python release_agent.py v1.3.0 "Breaking change" POC-2 "DEV,UAT,PRD" HIGH

Tempo medido: 8m 44s (inclui tempo de decisao humana).

## Rastreabilidade gerada automaticamente

Cada release produz:

- Tag e SHA no GitHub
- Run do GitHub Actions com deployment history
- GMUD no JSM com workflow ITIL completo
- Release Notes no Confluence com links cruzados para Jira, GMUD e pipeline
- Logs estruturados no Grafana Loki

## Componentes Cloud Run em producao

| Servico | Proposito |
|---|---|
| poc-oauth-dev | Aplicacao em DEV |
| poc-oauth-uat | Aplicacao em UAT |
| poc-oauth-prd | Aplicacao em PRD |
| gmud-bridge | Orquestrador event-driven JSM -> GitHub |

## Reproducao de um release

Standard Change (auto-aprovado):

    python release_agent.py v1.X.Y "Descricao" <JIRA_KEY> "DEV,UAT,PRD" LOW

Normal Change (requer CAB):

    python release_agent.py v1.X.Y "Descricao" <JIRA_KEY> "DEV,UAT,PRD" HIGH
