# PRODUCT_SPEC.md

## Propósito deste arquivo

Contexto de produto do servico construido neste repositorio. Os agentes da esteira Antigravity leem este arquivo antes de qualquer acao que impacte o produto (geracao de historias, arquitetura, codigo, testes, release).

Cada repositorio que passa pela esteira tem o seu proprio PRODUCT_SPEC.md. Se este repositorio for clonado como template para outro produto, este arquivo deve ser reescrito refletindo o novo contexto.

## Produto

**Nome:** OAuth Service
**Objetivo:** Expor endpoints de autenticacao, logout e callback integrando com Google Identity Platform
**Dominio:** autenticacao e controle de sessao

## Epic ativo

- **POC-1** - Autenticacao via Google OAuth

## Stories ativas

- **POC-2** - Autenticacao via conta Google
- **POC-3** - Provisionamento Automatico de Perfil (Just-in-Time)
- **POC-4** - Encerramento de Sessao (Logout) e Revogacao

## Personas

- **Usuario final** - acessa o servico via SSO
- **Admin de TI** - provisiona e revoga acessos
- **CAB** - aprova Normal Changes antes de deploy em producao

## Criterios de aceite globais

Valem para qualquer story deste produto, independente do escopo:

- Todo endpoint HTTP deve aceitar `GET /health` como liveness probe e retornar JSON com campos `status`, `service`, `env`, `version`
- Tokens emitidos devem ter TTL configuravel via variavel de ambiente
- Toda tentativa de autenticacao deve gerar registro de audit log estruturado em JSON
- Logout deve revogar o token no provedor de identidade, nao apenas invalidar sessao local
- Nenhuma senha pode ser armazenada localmente (SSO only)

## Estado atual da implementacao

A implementacao atual e um FastAPI minimo expondo `/health` e `/` (root), servindo como esqueleto para validar a esteira Antigravity end-to-end. As stories POC-2, POC-3 e POC-4 adicionarao a logica real de OAuth conforme forem priorizadas e processadas pela esteira.

## Versionamento deste arquivo

Atualize este arquivo quando:
- Novas stories forem priorizadas e entrarem no epic
- Novos criterios de aceite globais forem definidos
- O escopo do produto mudar (novos dominios, personas, etc)

Commits que modificam este arquivo devem usar prefixo `docs(spec):`
