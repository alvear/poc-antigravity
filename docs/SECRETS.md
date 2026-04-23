# Gestao de Segredos - POC Antigravity

## Filosofia

A POC segue o principio de secrets nunca em arquivo versionado. Segredos vivem em 2 lugares apenas:

1. **.env local** - para desenvolvimento. Arquivo nunca commitado (ver .gitignore).
2. **GCP Secret Manager** - para runtime em producao. Injetado no Cloud Run via --set-secrets.

Nenhum segredo deve aparecer em:
- Codigo fonte
- Arquivos de configuracao commitados
- Variaveis de ambiente de CI/CD que nao sejam secrets.* do GitHub Actions
- Logs (grafana_logger nao loga valores de tokens)

---

## Mapa de segredos

### Segredos de desenvolvimento local (no .env)

| Var | Como obter | Escopo | Rotacao |
|---|---|---|---|
| JIRA_TOKEN | id.atlassian.com/manage-profile/security/api-tokens | read/write em projetos Jira | Sob demanda |
| JIRA_EMAIL | Email da conta Atlassian | Identificacao | N/A |
| GITHUB_TOKEN | github.com/settings/tokens (PAT, scopes repo + workflow) | Escrita em um repo | A cada 90 dias recomendado |
| GRAFANA_TOKEN | grafana.com/orgs/<org>/api-keys | write:logs | A cada 180 dias recomendado |

### Segredos de runtime (Cloud Run, nao no .env)

| Var | Onde vive | Usado por |
|---|---|---|
| WEBHOOK_SECRET | GCP Secret Manager | gmud-bridge |
| JIRA_TOKEN (runtime) | GCP Secret Manager | gmud-bridge |
| GITHUB_TOKEN (runtime) | GCP Secret Manager | gmud-bridge |
| GRAFANA_TOKEN (runtime) | GCP Secret Manager | gmud-bridge + ci.yml |
| VERSION | Injetado pelo deploy.yml | src/main.py (/health) - metadado, nao segredo |

### Segredos da CI (GitHub Actions)

| Var | Como configurar |
|---|---|
| SONAR_TOKEN | sonarcloud.io/account/security |
| GRAFANA_LOKI_URL | Copy da conta Grafana |
| GRAFANA_USER | Copy da conta Grafana |
| GRAFANA_TOKEN | grafana.com/orgs/<org>/api-keys |

---

## Processo de rotacao

### Quando rotacionar
- Imediatamente apos suspeita de vazamento
- Apos saida de colaborador que tinha acesso
- Em schedule periodico (ver tabela acima)
- Apos upgrade que redefine escopos necessarios

### Como rotacionar (processo generico)
1. Criar novo token na plataforma correspondente
2. Atualizar os 3 lugares possiveis, na ordem:
   a. .env local do desenvolvedor
   b. GCP Secret Manager (gcloud secrets versions add)
   c. GitHub Actions secrets (UI ou gh secret set)
3. Revogar o token antigo SO DEPOIS de confirmar que o novo funciona
4. Validar cada integracao com scripts de teste

### Procedimento por plataforma

**Jira / JSM (Atlassian)**
- Acesse id.atlassian.com/manage-profile/security/api-tokens
- Create API token com label descritivo (ex: poc-antigravity-2026-04)
- Copie o token (so mostra uma vez)
- Atualize .env: JIRA_TOKEN=<novo>
- Atualize Secret Manager com gcloud secrets versions add jira-token
- Teste com: python jira_helper.py list
- Revogue o token antigo na UI

**GitHub PAT**
- Acesse github.com/settings/tokens
- Generate new token (classic) com scopes: repo + workflow
- Copie o token
- Atualize .env: GITHUB_TOKEN=<novo>
- Atualize Secret Manager com gcloud secrets versions add github-token
- Teste validacao do github_helper
- Delete o token antigo na UI

**Grafana Cloud**
- Acesse grafana.com/orgs/<org>/api-keys
- Add API key com role: MetricsPublisher
- Copie o token
- Atualize .env: GRAFANA_TOKEN=<novo>
- Atualize Secret Manager com gcloud secrets versions add grafana-token
- Atualize GitHub Actions com gh secret set GRAFANA_TOKEN
- Teste rodando o CI e vendo se notify-grafana passa
- Delete a API key antiga

---

## Divida tecnica consciente

### Tokens expostos no chat de desenvolvimento (Abril/2026)

Durante o desenvolvimento da POC, os seguintes tokens foram expostos em logs de sessao:
- GitHub PAT
- Jira API token
- Grafana Cloud token

**Decisao consciente:** rotacao adiada ate o fim do periodo de desenvolvimento ativo. O risco e mitigado por:
- Repo publico com scope limitado
- POC em conta GCP pessoal sem dados de negocio
- Nenhum dos tokens da acesso a sistemas de producao real

**Acao futura obrigatoria:** antes deste piloto virar uso produtivo em organizacao real:
- Rotacionar os 3 tokens acima
- Trocar conta Atlassian por conta de servico dedicada
- Trocar GitHub PAT por GitHub App (menor privilegio, rotacao automatica)
- Confirmar que nenhum token antigo existe em backups ou historico de conversas

---

## Como um novo dev obtem os secrets

### Cenario A - Desenvolvedor interno da equipe

1. Request no canal de onboarding do time
2. Recebera acesso a vault do time contendo os secrets
3. Copia pro .env local e desenvolve

### Cenario B - Colaborador externo

1. Fork o repositorio
2. Cria suas proprias contas em:
   - Atlassian (free tier)
   - GitHub (pessoal)
   - Grafana Cloud (free tier)
3. Gera os proprios tokens
4. Popula .env local com valores proprios
5. Deploy em GCP pessoal (projeto proprio)

Nao e possivel rodar a esteira contra o Jira/Confluence do dono da POC sem acesso autorizado.

---

## Referencias

- GitHub Secrets docs: docs.github.com/en/actions/security-guides/encrypted-secrets
- GCP Secret Manager: cloud.google.com/secret-manager/docs
- Atlassian API tokens: support.atlassian.com/atlassian-account/docs/manage-api-tokens-for-your-atlassian-account/
- Grafana Cloud tokens: grafana.com/docs/grafana-cloud/account-management/authentication-and-permissions/api-keys/
