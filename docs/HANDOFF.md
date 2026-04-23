# HANDOFF.md - Transicao V1 -> V2

> **Documento oficial do pivote arquitetural de 24/04/2026.**  
> Registro para referencia futura (voce, outro dev do time, outra sessao de IA).

---

## TL;DR

POC Antigravity V1 foi **pausada** em 24/04/2026 apos entrega de Blocos C + H
Parte A + Parte B. O paradigma inicial (agentes Python autonomos) foi
ressignificado: V2 adota paradigma **IDE-centric com Gemini embutido no
Antigravity**, proximo ao que o Devin prometeu mas dentro do editor.

V1 fica **congelada mas funcional** em github.com/alvear/poc-antigravity
(branch main). V2 comeca em repositorio novo, aproveitando 80% da infra-
estrutura, contexto de negocio e documentacao.

---

## Por que a V1 foi pausada

### Motivo tecnico

V1 comecou no Sprint 1 com rules.md descrevendo agentes como **personas** a
serem "vestidas" pelo Gemini do Antigravity (paradigma IDE-centric). A partir
do Sprint 3 (BaseAgent), evoluiu silenciosamente para **agentes Python
autonomos** (paradigma como LangChain, AutoGen, CrewAI).

A tensao entre os dois paradigmas ficou explicita na sessao de 24/04/2026,
quando o PM Agent exigiu integracao com LLM externo (Gemini API ou Claude API).
Surgiu a pergunta:

> "Por que eu preciso pagar API de Gemini se ja tenho Gemini embutido no
> Antigravity que e o editor que uso?"

A resposta honesta: os dois paradigmas sao **validos mas mutuamente
excludentes** em arquitetura pura. V1 estava tentando ser os dois ao mesmo
tempo, sem decisao consciente.

### Motivo estrategico

Visao original do Alvear era clara: **"Antigravity como um Devin, so que mais
parrudo"**. Devin = agente que vive dentro do IDE, conversa com o usuario,
executa tarefas com tools. V1 se afastou dessa visao ao codificar agentes como
classes Python autonomas.

Seguir pra Arquitetura Python pura seria abandonar a visao original. Seguir
pra Arquitetura IDE-centric exige restart limpo com paradigma explicito.

---

## Estado final da V1 (o que fica congelado)

### Entregue em main e funcionando

- Stack completa (GCP, Jira, Confluence, JSM, Grafana, SonarCloud)
- 7 helpers Python (jira, github, confluence, jsm, grafana, archi, gate)
- 3 agentes autonomos Python (Release, Reviewer, QA) + BaseAgent
- 137 testes, 100% coverage em src/, 6/6 gates de CI verdes
- 27 padroes arquiteturais documentados em `.antigravity/agent_guidelines.md`
  (91KB - Parte A fundamentos + Parte B agenticos)
- Governanca de qualidade via CI (Bandit, Safety, Checkov, Trivy, SonarCloud)
- Rastreabilidade end-to-end (Jira <-> GitHub <-> Grafana <-> JSM)

### Planejado mas nao implementado

7 agentes novos + Bloco D (QA v2). Total estimado: ~22-30h. Ficam no roadmap
de V1 mas nao serao implementados nesse paradigma. Em V2, parte desses
agentes vira **persona do Gemini no editor**, nao classe Python.

Ver `POC_ESTADO_ATUAL.md` secao "Itens planejados que NAO foram implementados".

---

## Estrategia da V2

### Paradigma

**IDE-centric: Gemini do Antigravity opera como motor de raciocinio dos
agentes, guiado por documentacao estruturada (`rules.md` + `agent_guidelines.md`)
e equipado com helpers Python como tools.**

### Arquitetura conceitual V2

Humano (Alvear) dentro do Antigravity
  │
  ├─ Conversa com Gemini assumindo persona ("seja o PM Agent")
  │    Gemini le: .antigravity/rules.md (persona + fluxo)
  │               .antigravity/agent_guidelines.md (padroes arquiteturais)
  │               PRODUCT_SPEC.md + TECH_STACK.md (contexto)
  │    Gemini raciocina e propoe acoes
  │
  ├─ Humano aprova/ajusta as propostas
  │
  ├─ Gemini executa helpers Python como tools (jira_helper, github_helper, ...)
  │
  └─ Resultado: artefatos em Jira/GitHub/Confluence (Modelo A de comunicacao)

Gates automatizados (CI, Reviewer, Release) continuam rodando em paralelo
como classes Python autonomas - essas funcionam bem em paradigma determinístico.

### Componentes reusaveis de V1 em V2

Ver `POC_ESTADO_ATUAL.md` secao "Componentes reusaveis em V2". Resumo:

- **100% reusaveis:** .env, config.py, 7 helpers, 91KB de guidelines, CI, keys
- **Parcialmente reusaveis:** rules.md (refinar pra formato persona)
- **NAO reusaveis:** agents/*.py + exceptions + shims + testes de agentes
  (paradigma diferente - ficam em V1 congelada)

### Reuso de infraestrutura

- **Repo GitHub:** V2 em repositorio novo (github.com/alvear/poc-antigravity-v2)
  V1 permanece em github.com/alvear/poc-antigravity
- **Jira projeto POC + Confluence space POCAntigra:** reusados em V2
  (contexto de negocio acumulado vale manter)
- **Todas as keys existentes:** reusadas em V2 (GitHub PAT, Jira token,
  Grafana, SonarCloud, GCP, JSM)
- **Gemini:** V2 usa Gemini embutido do Antigravity (sem API key externa
  inicialmente). Se futuramente V2 precisar Gemini em contexto Python,
  cria key separada no Google AI Studio

---

## Como retomar V2 (proximas acoes)

### Sessao 1 da V2 (nao esta sessao)

1. Criar repo github.com/alvear/poc-antigravity-v2
2. Copiar arquivos da V1 (config.py, helpers, rules, guidelines, CI, docs)
3. Criar `docs/adr/0001-paradigma-ide-centric.md` registrando a decisao
   com rigor
4. Refinar `.antigravity/rules.md` para ser **prompt-friendly** pro Gemini:
   - Cada agente (PM, Architect, Designer, Developer, Security\*) vira
     secao estruturada com "Persona", "Fluxo", "Tools disponiveis",
     "Exemplos de interacao"
5. Primeiro teste pratico: operar "PM Agent" via chat do Antigravity,
   validando que o Gemini consegue assumir a persona e executar o fluxo
   consultando rules + guidelines + helpers

### Criterios para retomar V1 (caso faca sentido)

Se no futuro aparecer alguma destas necessidades, V1 pode ser retomada:

- Cliente exigir agentes executando **sem editor aberto** (CI, cron,
  triggers de webhook)
- Esteira precisar ser **compartilhada por time grande** sem dependencia
  de IDE proprietario
- Auditoria/compliance exigir **trail formal e rastreavel em codigo**
  versionado (nao em conversas de editor)
- Necessidade de **testar agentes com framework de testes automatizado**
  (evals, regressao, etc)

Se nenhum destes aparecer, V1 permanece congelada. V2 e o caminho principal.

---

## Checkpoints e decisoes importantes (timeline)

- **Inicio 2026:** POC comeca como "Antigravity like Devin" no paradigma
  IDE-centric (rules.md + PM/Architect/Dev como personas)
- **Sprint 3:** BaseAgent criado - pivote silencioso para agentes Python
  autonomos
- **Sprints 3-5 + Bloco C:** ReleaseAgent, QAAgent, ReviewerAgent implementados
  como classes Python (137 testes, 6/6 CI)
- **Bloco H Parte A (19/04):** 16 padroes classicos em agent_guidelines.md
- **Bloco H Parte B (24/04):** 11 padroes agenticos em agent_guidelines.md
- **24/04 sessao da tarde:** discussao sobre PM Agent revela tensao entre
  paradigmas. Decisao consciente de **pausar V1 e abrir V2 no paradigma
  IDE-centric original**
- **Proxima sessao:** abertura da V2

---

## Arquivos de referencia nesta transicao

- `POC_ESTADO_ATUAL.md` - estado consolidado da V1 (este repositorio)
- `_archive/POC_ESTADO_ATUAL_pre_v1_pause.md` - versao anterior do estado
- `_archive/SESSAO_24_ABR_2026_parte2.md` - log da sessao que decidiu pivote
- `.antigravity/agent_guidelines.md` - 27 padroes, principal ativo reutilizavel
- `.antigravity/rules.md` - regras operacionais, base pra refinamento em V2

---

## Reflexoes finais da V1

V1 nao e fracasso. Entregou:

- Infraestrutura solida (GCP + Atlassian + GitHub + Grafana + SonarCloud)
- 91KB de documentacao estruturada (27 padroes em format template uniforme)
- 137 testes unitarios/integracao validando helpers e agentes determinísticos
- 6 gates de CI cobrindo SAST/SCA/IaC/Container/Quality
- Padroes consolidados (coverage 80%, Trivy bloqueante, conventional commits,
  modelo A de comunicacao entre agentes, hierarquia de excecoes)
- Lessons learned registradas

V2 comeca em cima disso. 80% do trabalho de V1 vira ativo de V2. Restante 20%
(agentes Python autonomos) fica como conhecimento adquirido - demonstra que
sabemos fazer agentes autonomos tambem, escolhendo IDE-centric por valor
estrategico e nao por limitacao tecnica.

Fechamento limpo, pivote consciente, futuro claro.

---

*Documento criado em 24/04/2026, ultima sessao ativa da V1.*
