# .antigravity/agent_guidelines.md

> Diretrizes que os agentes da esteira Antigravity aplicam ao gerar codigo,
> documentos e decisoes para aplicacoes novas.
>
> Este arquivo e lido pelos agentes ANTES de qualquer acao de geracao.
> Nao confundir com `.antigravity/rules.md` (regras operacionais por agente)
> nem com `PRODUCT_SPEC.md` / `TECH_STACK.md` (contexto do repositorio alvo).

---

## Estrutura

- **Parte A - Fundamentos de Software** (16 padroes classicos)
- **Parte B - Padroes Agenticos Modernos** (10 padroes especificos de sistemas LLM)
- **Parte C - Stack-Dependent** (14 padroes condicionais, revisitar quando aplicavel)

---

## Como o agente le este documento

1. Antes de qualquer geracao, agente le este arquivo.
2. Para cada padrao aplicavel ao tipo de tarefa em curso, segue a secao
   "Como o agente aplica".
3. Em caso de conflito entre padroes, prioridade vai para padroes da Parte A
   sobre B sobre C.
4. Em caso de excecao (situacao descrita em "Quando NAO aplicar"), o agente
   documenta a excecao em ADR e segue.

---

## Versionamento

Este arquivo e versionado em SemVer proprio. Ver CHANGELOG no fim.

---

## Principio meta

Padroes sem enforcement viram folclore. Cada padrao neste documento OU tem
enforcement automatico (regra do Reviewer ou check de CI), OU e marcado
explicitamente como "manual review".

---

## Sumario

### Parte A - Fundamentos de Software

1. Clean Architecture
2. Clean Code
3. Piramide de Testes
4. DDD - Bounded Contexts
5. BDD - Behavior Driven Development
6. Design por Contrato
7. 12-Factor App
8. Circuit Breaker
9. Saga Pattern
10. Zero Trust
11. Event Sourcing
12. Tiered Memory
13. TOGAF (diretriz arquitetural)
14. BIAN (diretriz arquitetural - bancario)
15. SRE - Site Reliability Engineering (diretriz arquitetural)
16. Chaos Engineering (diretriz arquitetural)

### Parte B - Padroes Agenticos Modernos

A definir em sub-sessao posterior.

### Parte C - Stack-Dependent

A definir em sub-sessao posterior.

---

## Parte A - Fundamentos de Software

---

## 1. Clean Architecture

**Camada:** Estrutura

**Aplicavel a:** Developer Agent, Architect Agent

### O que e

Organizacao do codigo em camadas concentricas, com dependencias fluindo apenas
de fora para dentro. As camadas tipicas sao: domain (regras de negocio puras),
application (casos de uso), infrastructure (adapters externos como DB, HTTP, filas).
A camada interna nunca conhece a externa.

### Por que aplicar

- Permite trocar infraestrutura (DB, framework HTTP, fila) sem reescrever regra de negocio.
- Testes unitarios da camada domain rodam sem mock de infra (sao funcoes puras).
- Reduz acoplamento entre regras de negocio e detalhes tecnicos.
- Facilita evolucao: adicionar nova interface (CLI, gRPC, GraphQL) reusa todo o domain.

### Quando aplicar

Sempre, para qualquer aplicacao com logica de negocio nao-trivial: APIs REST,
servicos backend, workers, agentes que tomam decisoes baseadas em regras.

### Quando NAO aplicar

- Scripts utilitarios de menos de 200 linhas (overhead nao se paga).
- Prototipos descartaveis (PoCs throw-away com vida util de dias).
- Aplicacoes puramente CRUD onde nao ha regra de negocio (so passa dados de
  HTTP para DB sem transformacao).

### Como o agente aplica

Developer Agent ao gerar codigo Python deve criar a estrutura:

```
src/
  domain/          # entidades, value objects, regras puras
  application/     # use cases, orquestracao
  infrastructure/  # adapters: db, http_client, queue, file_storage
  main.py          # composition root - monta dependencias
```

Regras de import:

- domain/ NUNCA importa de application/ ou infrastructure/
- application/ pode importar de domain/, NUNCA de infrastructure/
- infrastructure/ pode importar de domain/ e application/
- main.py importa de tudo (e o unico que conhece o grafo completo)

Architect Agent ao desenhar arquitetura deve documentar as 3 camadas no ADR
inicial e listar quais responsabilidades vao em cada uma.

### Exemplo correto

```
src/
  domain/
    orders/
      order.py              # class Order, calcular_total()
      order_repository.py   # interface (Protocol) abstrata
  application/
    place_order.py          # use case usa OrderRepository (interface)
  infrastructure/
    sqlalchemy_order_repo.py  # implementa OrderRepository com SQLAlchemy
    http_router.py            # FastAPI router chama place_order use case
  main.py                   # injeta SqlalchemyOrderRepo no use case
```

### Anti-padrao

```python
# src/main.py - tudo misturado
from fastapi import FastAPI
import psycopg2

app = FastAPI()
conn = psycopg2.connect(...)

@app.post("/orders")
def create_order(items: list):
    # regra de negocio inline
    total = sum(i["price"] * i["qty"] for i in items)
    if total > 10000 and not items[0].get("approved"):
        raise ValueError("Pedido alto sem aprovacao")
    # SQL inline
    conn.execute("INSERT INTO orders (total) VALUES (%s)", (total,))
    return total
```

Problemas: regra de negocio acoplada a HTTP e a SQL. Impossivel testar
calculo de total sem subir banco. Trocar Postgres por outro DB exige reescrever
endpoint. Adicionar CLI duplica a logica.

### Enforcement

- **Reviewer hard violation (futuro):** se src/ tem apenas main.py com mais de
  100 linhas e sem subpastas domain/application/infrastructure, o Reviewer
  rejeita o PR como "missing layers".
- **Reviewer soft violation:** se infrastructure/ importa de application/ no
  sentido errado (depende de domain/ apenas), o Reviewer marca REQUEST_CHANGES.
- **Manual review:** validar se a separacao semantica das camadas faz sentido
  (automatico checa estrutura de pasta, humano checa se esta no lugar certo).

### Padroes relacionados

- DDD - Bounded Contexts (define O QUE vai em domain/)
- Design por Contrato (interfaces/protocols entre camadas)
- Piramide de Testes (domain = unit, infrastructure = integration)

---

## 2. Clean Code

**Camada:** Qualidade

**Aplicavel a:** Developer Agent, Reviewer Agent

### O que e

Conjunto de praticas para tornar codigo legivel, modular e auto-explicativo.
Nomes descritivos, funcoes curtas com responsabilidade unica, ausencia de
magic numbers, comentarios apenas onde codigo nao consegue explicar por si.

### Por que aplicar

- Codigo e lido 10x mais que escrito - tempo de manutencao domina TCO.
- Reduz custo cognitivo de onboarding de novos agentes ou desenvolvedores.
- Diminui bugs - codigo claro expoe falhas de logica que codigo opaco esconde.
- Habilita refactor seguro - testes pegam regressao quando intencao esta clara.

### Quando aplicar

Sempre, em qualquer codigo destinado a producao ou compartilhado.

### Quando NAO aplicar

- One-liners de exploracao em REPL ou notebook descartavel.
- Codigo gerado automaticamente (migrations, protobuf, openapi).

### Como o agente aplica

Developer Agent ao gerar codigo Python segue:

- Nomes: substantivos para classes/variaveis, verbos para funcoes. Sem abreviacoes
  obscuras (calc_t -> calcular_total).
- Funcoes: maximo 30 linhas. Se passar, extrai sub-funcao com nome descritivo.
- Magic numbers proibidos: literais numericos com significado de negocio viram
  constantes nomeadas (TAXA_JUROS_MENSAL = 0.02, nao 0.02 inline).
- Type hints obrigatorios em toda funcao publica (parametros + retorno).
- Docstrings em toda funcao publica em modulo de producao.
- Comentarios so para explicar PORQUE, nunca O QUE (codigo deve mostrar o que).

### Exemplo correto

```python
TAXA_JUROS_MENSAL = 0.02
PARCELAS_MAXIMAS = 12

def calcular_parcela(valor_total: float, num_parcelas: int) -> float:
    """Calcula valor da parcela com juros compostos mensais."""
    if num_parcelas > PARCELAS_MAXIMAS:
        raise ValueError(f"Maximo de {PARCELAS_MAXIMAS} parcelas")
    montante = valor_total * (1 + TAXA_JUROS_MENSAL) ** num_parcelas
    return montante / num_parcelas
```

### Anti-padrao

```python
def calc(v, n):
    # calcula parcela
    if n > 12:
        raise ValueError("erro")
    m = v * (1 + 0.02) ** n
    return m / n
```

Problemas: nomes obscuros (v, n, m, calc), magic numbers (12, 0.02), sem type
hints, docstring inutil, mensagem de erro vaga.

### Enforcement

- **Reviewer hard violation:** funcao publica sem type hints (ja implementado).
- **Reviewer soft violation:** funcao publica sem docstring (ja implementado).
- **Reviewer soft violation (futuro):** funcao com mais de 30 linhas.
- **Reviewer soft violation (futuro):** literais numericos suspeitos sem
  constante nomeada (regex de numeros nao-triviais em codigo de negocio).

### Padroes relacionados

- Design por Contrato (type hints sao parte de Clean Code e contratos)
- DDD - Bounded Contexts (nomes de classes refletem linguagem ubiqua do dominio)

---

## 3. Piramide de Testes

**Camada:** Validacao

**Aplicavel a:** QA Agent, Developer Agent

### O que e

Distribuicao proporcional dos testes automatizados em 3 camadas: unit (base larga),
integration (meio), e2e (topo estreito). Proporcao alvo padrao: 70/20/10.
Cada camada testa um escopo diferente com custo e velocidade diferentes.

### Por que aplicar

- Unit tests rodam em milissegundos, dao feedback rapido ao developer.
- Integration tests cobrem contratos entre camadas, pegam bugs de fronteira.
- E2E tests garantem fluxos de usuario, mas sao lentos e caros - poucos bastam.
- Inverter a piramide (muito e2e, pouco unit) gera suite lenta e fragil.

### Quando aplicar

Sempre, em qualquer aplicacao com testes automatizados.

### Quando NAO aplicar

- Bibliotecas puras sem IO (so unit tests fazem sentido).
- Scripts de uma unica execucao (testes nao se pagam).

### Como o agente aplica

QA Agent gera testes em 3 modos distintos respeitando a proporcao do TECH_STACK
do repositorio alvo (default 70/20/10):

- **Unit (70%):** testa funcao/classe isolada, com @patch ou MagicMock para deps.
  Roda sem rede, banco ou sistema de arquivos. Localizacao: tests/unit/
- **Integration (20%):** testa fluxo entre camadas, usa TestClient/AsyncClient
  ou fixtures com banco real (testcontainers). Localizacao: tests/integration/
- **E2E (10%):** testa cenario de usuario end-to-end, marcado com
  @pytest.mark.e2e. Localizacao: tests/e2e/

### Exemplo correto

Estrutura de testes para um endpoint POST /orders:

```
tests/
  unit/
    test_order_service.py     # testa Order.calcular_total isolado
  integration/
    test_orders_router.py     # testa POST /orders com TestClient + DB real
  e2e/
    test_order_flow.py        # testa: login -> add ao carrinho -> checkout
```

### Anti-padrao

100% e2e cobrindo todo o sistema via Selenium. Suite leva 40 minutos, falha
intermitente em 1 a cada 3 runs por timing, ninguem roda local.

### Enforcement

- **Manual review:** validar proporcao a cada release (futuro: comando QA Agent
  validate_pyramid percorrendo tests/ e reportando desvio).
- **Reviewer soft violation (futuro):** PR adiciona arquivo em src/ sem teste
  correspondente em tests/unit/ ou tests/integration/.

### Padroes relacionados

- BDD (E2E tipicamente usa Gherkin)
- Clean Architecture (unit testa domain/, integration testa infrastructure/)
- Design por Contrato (contratos sao base de testes de integracao)

---

## 4. DDD - Bounded Contexts

**Camada:** Dominio

**Aplicavel a:** Architect Agent, PM Agent, Developer Agent

### O que e

Domain-Driven Design organiza sistemas grandes em Bounded Contexts: divisoes
explicitas onde cada contexto tem seu proprio modelo, linguagem ubiqua e
limites claros. Conceito que aparece em 2 contextos pode ter significado
diferente em cada (ex: "Cliente" no contexto de Vendas vs no contexto de Cobranca).

### Por que aplicar

- Reduz acoplamento - mudanca em um contexto nao quebra outros.
- Permite times paralelos - cada contexto pode ser dono de um time.
- Modelo permanece coerente - nao tenta forcar conceitos que sao distintos.
- Habilita evolucao independente - contexto pode ser extraido como microservico.

### Quando aplicar

- Sistemas com mais de 3-4 dominios distintos de negocio.
- Aplicacoes que vao crescer em time ou complexidade.
- Refatoracao de monolitos legados.

### Quando NAO aplicar

- CRUDs simples com 1-2 entidades.
- Prototipos de validacao de hipotese.
- Scripts e ferramentas internas.

### Como o agente aplica

Architect Agent ao desenhar arquitetura inicial:

- Identifica contextos de negocio com PM Agent (entrevistas, eventos de dominio).
- Documenta cada contexto em ADR proprio com: nome, responsabilidades, linguagem
  ubiqua, eventos publicados, eventos consumidos.
- Define mapa de contexto (context map) com tipo de relacionamento entre contextos
  (Shared Kernel, Customer-Supplier, Anti-Corruption Layer, etc).

Developer Agent ao gerar codigo:

- Cria modulo por contexto sob src/domain/{contexto}/
- NUNCA importa entidade de outro contexto diretamente - sempre via Anti-Corruption
  Layer ou eventos.
- Linguagem dos nomes (classes, funcoes, variaveis) reflete a linguagem ubiqua
  do contexto - mesmo que conceitos pareçam duplicados em contextos diferentes.

### Exemplo correto

```
src/domain/
  vendas/
    cliente.py        # class Cliente: nome, email, historico_compras
    pedido.py
  cobranca/
    cliente.py        # class Cliente: nome, cpf, score_credito, dividas
    fatura.py
  estoque/
    produto.py        # class Produto: sku, quantidade, localizacao
```

Note que "Cliente" existe em vendas/ e em cobranca/. Sao classes diferentes,
porque o conceito de Cliente nesses dois contextos e diferente.

### Anti-padrao

```
src/models/
  cliente.py    # class Cliente: nome, email, cpf, historico, score, dividas, ...
```

Uma unica classe Cliente com TODOS os campos de TODOS os contextos. Resultado:
mudanca em Cobranca quebra Vendas, time de Cobranca nao pode mexer sem alinhar
com Vendas, classe vira monstro de 50+ campos com varios opcionais.

### Enforcement

- **Manual review:** validar se a divisao de contextos faz sentido para o dominio.
- **Reviewer soft violation (futuro):** import direto entre src/domain/A e
  src/domain/B sem passar por anti_corruption/.
- **Architect Agent enforcement:** ADR de novo contexto exige documentar
  linguagem ubiqua e mapa de relacionamento com contextos existentes.

### Padroes relacionados

- Clean Architecture (Bounded Context define O QUE vai em domain/)
- Event-Driven (Parte C - comunicacao entre contextos via eventos)
- Saga Pattern (transacoes que cruzam contextos)

---

## 5. BDD - Behavior Driven Development

**Camada:** Requisitos

**Aplicavel a:** PM Agent, QA Agent, Developer Agent

### O que e

Especificacao de comportamento esperado em formato executavel, usando linguagem
estruturada (Gherkin) que stakeholders nao-tecnicos conseguem ler. Cenarios sao
escritos como Given-When-Then antes do codigo, e viram testes automatizados que
validam o comportamento.

### Por que aplicar

- Especificacao vira teste - elimina divergencia entre o que foi pedido e o que
  foi feito.
- Linguagem comum - PM, dev, QA e cliente usam o mesmo vocabulario.
- Documentacao viva - cenarios sempre refletem comportamento real (testes
  quebram se divergir).
- Cobre fluxos de usuario, nao apenas funcoes.

### Quando aplicar

- Features com regras de negocio complexas.
- Sistemas com multiplos stakeholders nao-tecnicos.
- Testes E2E (camada topo da piramide).

### Quando NAO aplicar

- Funcoes utilitarias puras (overhead de Gherkin nao se paga).
- APIs internas consumidas so por outros sistemas (testes de contrato bastam).
- Bibliotecas tecnicas sem cenarios de usuario.

### Como o agente aplica

PM Agent ao registrar historia no Jira:

- Inclui cenarios em Gherkin (Given-When-Then) na descricao do card.
- Pelo menos 1 cenario happy path + 1-2 cenarios de erro/edge case.

QA Agent ao gerar testes E2E:

- Le os cenarios Gherkin do card Jira.
- Gera arquivo .feature em tests/e2e/features/
- Gera step definitions em tests/e2e/test_*.py usando pytest-bdd.

Developer Agent:

- Antes de implementar, le os cenarios para entender comportamento esperado.

### Exemplo correto

```
# tests/e2e/features/checkout.feature
Feature: Checkout de pedido com cupom

  Scenario: Aplicar cupom valido
    Given que tenho 2 produtos no carrinho totalizando R$ 100
    And o cupom "DESCONTO10" oferece 10% off
    When aplico o cupom no checkout
    Then o total final e R$ 90
    And o cupom marca como usado
```

```python
# tests/e2e/test_checkout.py
from pytest_bdd import scenarios, given, when, then

scenarios("../features/checkout.feature")

@given("que tenho 2 produtos no carrinho totalizando R$ 100")
def setup_cart(cart):
    cart.add(produto_id="P1", price=60)
    cart.add(produto_id="P2", price=40)
```

### Anti-padrao

Especificacoes em wiki paragrafos longos sem cenarios concretos. Resultado: PM,
dev e QA interpretam diferente, bug aparece em prod, ninguem sabe se era bug
ou feature.

### Enforcement

- **Manual review:** PM Agent pode validar se cenarios cobrem casos relevantes.
- **QA Agent check:** historia sem cenarios Gherkin gera REQUEST_CHANGES no PM.
- **Reviewer soft violation (futuro):** PR de feature complexa sem teste E2E
  correspondente em tests/e2e/.

### Padroes relacionados

- Piramide de Testes (BDD tipicamente cobre o topo - E2E)
- DDD - Bounded Contexts (linguagem dos cenarios = linguagem ubiqua)

---

## 6. Design por Contrato

**Camada:** Contratos

**Aplicavel a:** Developer Agent, Architect Agent, Reviewer Agent

### O que e

Toda interface publica (funcao, endpoint HTTP, mensagem de fila) declara
explicitamente: tipos de entrada, tipos de saida, pre-condicoes (o que precisa
ser verdade antes da chamada) e pos-condicoes (o que sera verdade depois).
Contratos sao verificados estaticamente (type checker) e dinamicamente (validacao).

### Por que aplicar

- Erros aparecem na fronteira (entrada invalida) e nao 5 camadas abaixo.
- IDE e linter ajudam - autocomplete e deteccao de bugs antes do runtime.
- Refactor seguro - mudar contrato quebra build em todos os usos, forcando atualizacao.
- Documentacao automatica - tipo eh documentacao executavel.

### Quando aplicar

Sempre, em qualquer interface publica: funcoes exportadas, endpoints HTTP,
handlers de mensagem, schemas de evento.

### Quando NAO aplicar

- Funcoes privadas (prefixo _) com escopo de modulo, podem ter type hints
  opcionais.
- Scripts one-off de exploracao.

### Como o agente aplica

Developer Agent ao gerar codigo Python:

- Type hints obrigatorios em toda funcao publica (parametros + retorno).
- Pydantic models para representar entrada/saida de boundary (HTTP, fila, disco).
- Validacao de invariantes no construtor de entidades de dominio.
- Erros customizados (subclasses de Exception) para violacao de contrato, com
  mensagem clara do que falhou.

Architect Agent:

- Toda integracao entre servicos especifica contrato (OpenAPI, JSON Schema,
  Protobuf) antes da implementacao.

### Exemplo correto

```python
from pydantic import BaseModel, Field, EmailStr

class CriarUsuarioRequest(BaseModel):
    nome: str = Field(min_length=2, max_length=100)
    email: EmailStr
    idade: int = Field(ge=18, le=120)

class CriarUsuarioResponse(BaseModel):
    id: int
    nome: str
    email: EmailStr

def criar_usuario(req: CriarUsuarioRequest) -> CriarUsuarioResponse:
    """Cria usuario. Pre: email nao existe. Pos: id > 0."""
    if usuario_existe(req.email):
        raise UsuarioJaExisteError(email=req.email)
    novo = repo.salvar(req)
    return CriarUsuarioResponse(id=novo.id, nome=novo.nome, email=novo.email)
```

### Anti-padrao

```python
def criar_usuario(dados):
    if "email" not in dados:
        return {"erro": "falta email"}
    if not isinstance(dados.get("idade"), int):
        return {"erro": "idade invalida"}
    novo = repo.salvar(dados)
    return novo
```

Problemas: contrato implicito (so descobre o que e dados na hora), validacao
ad-hoc espalhada, erro como dict (chamador esquece de checar), retorno sem tipo.

### Enforcement

- **Reviewer hard violation:** funcao publica sem type hints (ja implementado).
- **Reviewer soft violation (futuro):** funcao recebe dict cru em vez de Pydantic
  model em boundary HTTP.
- **CI check (futuro):** mypy strict mode em src/ - falha se algum tipo for Any
  implicito.

### Padroes relacionados

- Clean Code (type hints fazem parte de Clean Code)
- Clean Architecture (contratos definem fronteira entre camadas)
- Saga Pattern (contratos formais entre etapas da saga)

---

## 7. 12-Factor App

**Camada:** Operacao

**Aplicavel a:** Developer Agent, Architect Agent

### O que e

Conjunto de 12 praticas para construir aplicacoes nativas de nuvem: stateless,
configuracao via env vars, dependencias declaradas explicitamente, logs como
stream, processos descartaveis, paridade entre dev e prod. Originalmente
publicado pela Heroku, virou padrao de fato para servicos modernos.

### Por que aplicar

- Habilita deploy em qualquer plataforma (Cloud Run, K8s, ECS, Heroku).
- Escala horizontal trivial - basta adicionar instancias.
- Recuperacao de falhas trivial - processos podem ser mortos e restartados.
- Reduz drift entre ambientes - dev e prod usam mesmo binario com configs distintas.

### Quando aplicar

Sempre, para qualquer servico backend ou worker que vai rodar em producao.

### Quando NAO aplicar

- Aplicacoes desktop nativas.
- Sistemas embarcados.
- Scripts CLI de uso unico.

### Como o agente aplica

Developer Agent ao gerar servicos:

- **Config:** toda configuracao vem de env vars, validadas via pydantic-settings.
  Zero hardcode de URLs, credenciais, feature flags.
- **Stateless:** processo nao guarda estado entre requests. Estado vai para
  banco, cache externo (Redis) ou fila.
- **Logs:** escreve em stdout/stderr como stream de eventos (JSON estruturado
  preferido). NUNCA escreve em arquivo de log.
- **Dependencias:** declaradas em requirements.txt (Python) ou equivalente,
  versoes pinadas.
- **Build, release, run:** etapas separadas - build gera artefato, release
  combina com config, run executa.
- **Disposability:** processo inicia em segundos e para gracefully no SIGTERM.
- **Backing services:** banco, cache, fila sao recursos anexaveis - trocaveis
  via env var sem mudanca de codigo.

Architect Agent:

- ADR de novo servico documenta como cada um dos 12 fatores foi atendido (ou
  por que algum nao se aplica).

### Exemplo correto

```python
# config.py
from pydantic_settings import BaseSettings
from pydantic import SecretStr

class Settings(BaseSettings):
    database_url: SecretStr
    redis_url: SecretStr
    log_level: str = "INFO"

    class Config:
        env_file = ".env"

settings = Settings()
```

```
# Dockerfile
FROM python:3.12-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
USER 1000
CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8080"]
```

### Anti-padrao

- Hardcode de "https://api.prod.example.com" em codigo.
- Logs em /var/log/app.log dentro do container.
- Processo lento para iniciar (60s+) por carregar 5GB de modelo na memoria.
- Sessao HTTP guardada em memoria do processo (perde no restart).

### Enforcement

- **Reviewer hard violation:** credenciais hardcoded (ja implementado).
- **Reviewer soft violation (futuro):** uso de open() para escrever log file.
- **Architect Agent check:** ADR de servico sem secao "12-factor compliance"
  e devolvido para revisao.

### Padroes relacionados

- Zero Trust (config via env reduz risco de credenciais em codigo)
- Clean Architecture (config externa eh parte da camada infrastructure)

---

## 8. Circuit Breaker

**Camada:** Resiliencia

**Aplicavel a:** Developer Agent, Architect Agent

### O que e

Padrao para proteger sistemas de cascata de falhas em chamadas a servicos
externos. O breaker monitora taxa de erro - quando passa do limiar, "abre" e
para de fazer chamadas por um tempo, retornando erro imediato ao chamador.
Apos timeout, tenta novamente em estado "half-open".

### Por que aplicar

- Evita esgotar pool de conexoes esperando timeout em servico caido.
- Da tempo para servico downstream se recuperar (sem ser bombardeado).
- Falha rapido em vez de lento - chamador decide fallback.
- Contem propagacao de falha - servico A nao derruba B, C, D em cadeia.

### Quando aplicar

Toda chamada de rede para servico externo: APIs HTTP, banco de dados, cache,
filas, MCP servers. Especialmente quando o chamador serve trafego do usuario.

### Quando NAO aplicar

- Chamadas a recursos locais (filesystem, processo filho controlado).
- Scripts batch que podem esperar - retry simples basta.

### Como o agente aplica

Developer Agent ao gerar codigo que chama servico externo:

- Wrap cada cliente HTTP com biblioteca de circuit breaker (ex: pybreaker, tenacity).
- Configuracao padrao: abre apos 5 falhas em 60s, half-open apos 30s, fecha apos
  3 sucessos consecutivos.
- Timeout explicito sempre - nunca usar default infinito.
- Retry com exponential backoff (max 3 tentativas, base 1s).
- Em erro de breaker aberto, retorna fallback (cache, valor default, mensagem
  amigavel) ou propaga erro estruturado.

Architect Agent:

- Toda integracao externa documenta no ADR: timeout, retry policy, breaker
  policy, fallback.

### Exemplo correto

```python
import httpx
import pybreaker

cep_breaker = pybreaker.CircuitBreaker(fail_max=5, reset_timeout=30)

@cep_breaker
async def consultar_cep(cep: str) -> dict:
    async with httpx.AsyncClient(timeout=2.0) as client:
        r = await client.get(f"https://viacep.com.br/ws/{cep}/json/")
        r.raise_for_status()
        return r.json()

async def buscar_endereco_com_fallback(cep: str) -> dict:
    try:
        return await consultar_cep(cep)
    except pybreaker.CircuitBreakerError:
        return {"cep": cep, "fonte": "indisponivel"}
```

### Anti-padrao

```python
def consultar_cep(cep):
    r = requests.get(f"https://viacep.com.br/ws/{cep}/json/")
    return r.json()
```

Problemas: sem timeout (request pode pendurar), sem retry, sem breaker. Quando
ViaCEP cair, este servico cai junto - cada chamada espera 30s+ ate a conexao
estourar.

### Enforcement

- **Reviewer soft violation (futuro):** uso de requests.get/post sem timeout
  explicito.
- **Manual review:** validar se chamadas externas tem politica de breaker
  documentada.
- **Architect Agent check:** ADR de integracao sem secao "resilience policy"
  eh devolvido.

### Padroes relacionados

- SRE (breaker eh implementacao concreta de SLO de disponibilidade)
- Saga Pattern (breaker pode disparar compensacao em saga)
- 12-Factor App (breaker faz parte de "disposability" e graceful degradation)

---

## 9. Saga Pattern

**Camada:** Consistencia

**Aplicavel a:** Architect Agent, Developer Agent

### O que e

Padrao para gerenciar transacoes que cruzam multiplos servicos ou Bounded
Contexts, onde transacao distribuida classica (2-phase commit) nao se aplica.
Cada etapa local commita imediatamente, e cada uma tem uma acao de compensacao
inversa que e executada se etapas posteriores falharem.

### Por que aplicar

- Garante consistencia eventual em fluxos longos sem locks distribuidos.
- Permite servicos independentes (cada um dono do proprio dado).
- Falhas em qualquer etapa tem caminho explicito de rollback.
- Auditoria completa - cada etapa e cada compensacao sao eventos rastreaveis.

### Quando aplicar

- Fluxos que envolvem 2+ servicos ou contextos com mudanca de estado em cada.
- Transacoes longas (mais de poucos segundos) onde locks nao sao viaveis.
- Operacoes onde rollback automatico de DB nao basta (precisa desfazer email
  enviado, cobranca feita, etc).

### Quando NAO aplicar

- Operacoes em um unico servico/contexto - transacao de DB local basta.
- Operacoes idempotentes que podem ser apenas re-tentadas.

### Como o agente aplica

Architect Agent ao desenhar fluxo distribuido:

- Identifica etapas: cada uma e uma transacao local commitada.
- Define compensacao para cada etapa (pode ser no-op se etapa anterior nao
  produz efeito desfazivel).
- Decide entre orquestracao (um servico coordena) ou coreografia (servicos
  reagem a eventos).
- Documenta saga em ADR: etapas, eventos publicados, eventos consumidos,
  compensacoes, tratamento de falha de compensacao.

Developer Agent ao implementar:

- Toda etapa publica evento "X completed" ou "X failed".
- Compensacoes sao idempotentes (podem ser executadas multiplas vezes sem
  efeito colateral).
- Estado da saga eh persistido (banco, fila com TTL longo) para sobreviver
  a restart do servico.

### Exemplo correto

Fluxo de compra com 3 etapas:

```
1. Reservar estoque       -> compensa: liberar estoque
2. Cobrar cartao          -> compensa: estornar cobranca
3. Criar pedido           -> compensa: cancelar pedido

Se passo 3 falha:
  -> executa compensacao do passo 2 (estornar cobranca)
  -> executa compensacao do passo 1 (liberar estoque)
  -> publica evento "compra falhou" para usuario
```

### Anti-padrao

Tentar transacao distribuida ACID classica usando 2PC entre servicos. Resultado:
locks distribuidos, deadlocks frequentes, sistema travado quando um servico
fica lento, recuperacao manual em caso de coordenador caido.

Pior anti-padrao: iniciar fluxo, deixar pela metade, sem compensacao - resulta
em estoque reservado pra sempre, cobranca sem pedido, etc.

### Enforcement

- **Manual review:** Architect Agent valida se cada etapa tem compensacao
  documentada.
- **Reviewer soft violation (futuro):** PR introduz fluxo multi-servico sem
  ADR de saga correspondente.

### Padroes relacionados

- DDD - Bounded Contexts (sagas sao a forma de coordenar contextos)
- Event Sourcing (eventos da saga viram audit trail natural)
- Circuit Breaker (cada etapa pode ter seu breaker)

---

## 10. Zero Trust

**Camada:** Seguranca

**Aplicavel a:** Architect Agent, Developer Agent, Reviewer Agent

### O que e

Modelo de seguranca que assume rede interna e externa igualmente nao-confiaveis.
Toda requisicao e autenticada, autorizada e validada, mesmo entre componentes
do mesmo sistema. "Never trust, always verify". Substitui o modelo classico de
"perimetro de rede confiavel".

### Por que aplicar

- Reduz dano de breach - atacante que entra em um servico nao acessa todo o
  sistema livremente.
- Aplicavel em ambiente de cloud onde "rede interna" eh ilusao (multi-tenant,
  shared infrastructure).
- Habilita mTLS entre servicos, auditoria completa de acessos.
- Forca o time a documentar e versionar permissoes (politicas como codigo).

### Quando aplicar

Sempre, em qualquer aplicacao que processa dados de usuarios ou tem componentes
distribuidos. Nivel de rigor varia (POC interna vs sistema bancario).

### Quando NAO aplicar

- Scripts CLI locais executados pelo proprio usuario.
- Bibliotecas puras sem rede.

### Como o agente aplica

Developer Agent ao gerar codigo:

- **Autenticacao:** todo endpoint HTTP exige token (JWT, OAuth) - exceto health
  checks publicos explicitamente marcados.
- **Autorizacao:** decisao de "pode ou nao" em ponto centralizado (decorator,
  middleware), nao espalhada nos handlers.
- **Validacao:** toda entrada externa validada via Pydantic ou JSON Schema -
  inclui chamadas de servico para servico.
- **Secrets:** sempre via env var ou secret manager, nunca em codigo ou commit.
- **Logs:** registra todo acesso (quem, quando, o que, resultado).

Architect Agent:

- ADR de novo servico documenta: como autentica chamadas inbound, como
  autentica chamadas outbound, quais permissoes especificas exige.

### Exemplo correto

```python
from fastapi import Depends, HTTPException
from fastapi.security import HTTPBearer

security = HTTPBearer()

async def usuario_atual(token = Depends(security)) -> Usuario:
    try:
        payload = jwt.decode(token.credentials, settings.jwt_secret.get_secret_value())
        return Usuario(id=payload["sub"], roles=payload["roles"])
    except jwt.InvalidTokenError:
        raise HTTPException(401, "Token invalido")

def requer_role(role_necessaria: str):
    def check(usuario: Usuario = Depends(usuario_atual)) -> Usuario:
        if role_necessaria not in usuario.roles:
            log.warn("auth", "Acesso negado", usuario_id=usuario.id, role=role_necessaria)
            raise HTTPException(403, "Permissao insuficiente")
        return usuario
    return check

@app.delete("/usuarios/{id}")
async def excluir_usuario(id: int, _: Usuario = Depends(requer_role("admin"))):
    repo.excluir(id)
```

### Anti-padrao

```python
@app.delete("/usuarios/{id}")
async def excluir_usuario(id: int):
    repo.excluir(id)
```

Endpoint sensivel sem autenticacao nem autorizacao. Qualquer um na rede pode
chamar e excluir qualquer usuario.

### Enforcement

- **Reviewer hard violation:** credencial hardcoded (ja implementado, 6 patterns).
- **Reviewer hard violation:** .env commitado (ja implementado).
- **Reviewer soft violation (futuro):** endpoint que muda estado (POST/PUT/PATCH/DELETE)
  sem decorator de auth visivel.
- **Manual review:** Architect Agent valida ADR de novo servico contra checklist
  Zero Trust.

### Padroes relacionados

- 12-Factor App (secrets via env)
- Design por Contrato (validacao de entrada eh parte de contrato)
- SRE (auditoria de acessos eh parte de observabilidade)

---

## 11. Event Sourcing

**Camada:** Rastreabilidade

**Aplicavel a:** Architect Agent, Developer Agent

### O que e

Em vez de salvar apenas o estado atual de uma entidade, salva a sequencia
imutavel de eventos que produziram esse estado. Estado atual eh derivado da
soma dos eventos. Eventos passados nunca mudam - so novos sao adicionados.

### Por que aplicar

- Audit trail completo "de graca" - cada mudanca de estado eh um evento gravado.
- Time travel - reconstroi estado de qualquer momento no passado.
- Habilita debugging - reproduz bugs replicando sequencia de eventos.
- Desacopla producao e consumo - novos consumidores releem historico.

### Quando aplicar

- Dominios com requisito de auditoria forte (financeiro, saude, legal).
- Sistemas onde "como chegamos aqui" importa tanto quanto "onde estamos".
- Workflows complexos com varias etapas que precisam de rastreio.

### Quando NAO aplicar

- CRUDs simples sem requisito de auditoria.
- Sistemas com volume muito alto de mudancas onde overhead de eventos
  inviabiliza performance.
- Equipes pequenas sem experiencia - tem curva de aprendizado real.

### Como o agente aplica

Developer Agent ao implementar entidade event-sourced:

- Define eventos como classes imutaveis (frozen dataclass ou Pydantic frozen).
- Entidade tem metodo apply(event) que muta estado em memoria.
- Persistencia escreve eventos em event store (banco append-only).
- Snapshots periodicos para evitar replay de milhares de eventos.

Architect Agent:

- Decide quais agregados usam event sourcing - nem tudo precisa.
- Documenta esquema de cada evento (versao, payload, evolucao).
- Define politica de retencao e snapshots.

### Exemplo correto

```python
from dataclasses import dataclass
from datetime import datetime

@dataclass(frozen=True)
class PedidoCriado:
    pedido_id: str
    cliente_id: str
    timestamp: datetime

@dataclass(frozen=True)
class ItemAdicionado:
    pedido_id: str
    produto_id: str
    quantidade: int
    timestamp: datetime

class Pedido:
    def __init__(self):
        self.id = None
        self.cliente_id = None
        self.itens = []

    def apply(self, evento):
        if isinstance(evento, PedidoCriado):
            self.id = evento.pedido_id
            self.cliente_id = evento.cliente_id
        elif isinstance(evento, ItemAdicionado):
            self.itens.append({"produto": evento.produto_id, "qtd": evento.quantidade})

    @classmethod
    def reconstruir(cls, eventos: list):
        p = cls()
        for e in eventos:
            p.apply(e)
        return p
```

### Anti-padrao

Atualizar tabela "pedidos" diretamente com UPDATE, sem nenhum log de quem
mudou o que e quando. Resultado: alguem reclama "meu pedido foi alterado",
ninguem consegue investigar.

### Enforcement

- **Manual review:** Architect Agent decide quais agregados usam event sourcing
  no ADR de modelo de dados.
- **Reviewer soft violation (futuro):** UPDATE/DELETE em tabela marcada como
  event-sourced (so INSERT permitido).

### Padroes relacionados

- Saga Pattern (eventos da saga sao naturalmente event-sourced)
- DDD - Bounded Contexts (eventos respeitam fronteiras de contexto)
- Tiered Memory (eventos sao memoria longa imutavel)

---

## 12. Tiered Memory

**Camada:** Cognicao

**Aplicavel a:** Architect Agent, Developer Agent (so para apps agenticos)

### O que e

Padrao especifico para sistemas agenticos que precisam manter contexto ao longo
do tempo. Memoria estratificada em 3 niveis: curto prazo (contexto da execucao
atual), longo prazo (conhecimento persistente), episodica (sumarios de eventos
passados relevantes). Cada nivel tem custo, latencia e capacidade diferentes.

### Por que aplicar

- LLMs tem janela de contexto limitada - memoria externa estende capacidade.
- Reduz custo - evita reenviar todo o historico em cada chamada.
- Permite agentes evoluirem - aprendem com execucoes passadas.
- Habilita personalizacao - agente lembra preferencias do usuario.

### Quando aplicar

So em aplicacoes que sao elas proprias agenticas (usam LLM em loop, mantem
estado entre interacoes). Nao se aplica a backends/APIs tradicionais.

### Quando NAO aplicar

- APIs stateless tradicionais.
- Servicos que nao usam LLM.
- Agentes one-shot que nao precisam de contexto entre execucoes.

### Como o agente aplica

Developer Agent ao gerar app agentico:

- **Curto prazo (contexto):** janela de mensagens da conversa atual, mantida
  em memoria do processo ou cache (Redis com TTL curto).
- **Longo prazo (conhecimento):** vector store (pgvector, Pinecone, Weaviate)
  com embeddings de documentos, FAQ, decisoes anteriores.
- **Episodica (sumarios):** banco relacional com sumarios LLM-gerados de
  conversas/sessoes passadas, com metadados (usuario, timestamp, topico).

Cada chamada ao LLM monta prompt combinando: instrucoes (system) + memoria
longa relevante (RAG) + sumarios episodicos relevantes + contexto curto.

Architect Agent:

- Decide tecnologia de cada camada conforme stack.
- Define politica de retencao - quando sumarizar curto -> episodica, quando
  expirar episodica.

### Exemplo correto

```python
class TieredMemory:
    def __init__(self, cache, vector_store, episodic_db):
        self.short_term = cache
        self.long_term = vector_store
        self.episodic = episodic_db

    async def build_context(self, user_id: str, current_query: str) -> dict:
        return {
            "recent": await self.short_term.get(f"conv:{user_id}", limit=10),
            "knowledge": await self.long_term.similarity_search(current_query, k=3),
            "episodic": await self.episodic.relevant_summaries(user_id, current_query, k=2),
        }
```

### Anti-padrao

Mandar toda a historia da conversa ao LLM em cada chamada, sem memoria externa.
Resultado: contexto estoura em poucas trocas, custo cresce quadratico, LLM
"esquece" inicio da conversa quando window estoura.

### Enforcement

- **Manual review:** Architect Agent valida arquitetura de memoria de qualquer
  app agentico.
- **Manual review (futuro):** check de Token Budget acoplado a memoria.

### Padroes relacionados

- Event Sourcing (eventos sao memoria episodica natural)
- (Parte B) Token Budget Guardrails
- (Parte C) RAG e Hybrid Search

---

## 13. TOGAF

**Camada:** Estrategia

**Aplicavel a:** Architect Agent, PM Agent

**Tipo:** Diretriz arquitetural (nao gera codigo diretamente)

### O que e

The Open Group Architecture Framework. Metodologia para desenvolver e governar
arquitetura corporativa. Define um ciclo iterativo (ADM - Architecture
Development Method) com fases: visao, arquitetura de negocio, arquitetura de
sistemas, arquitetura tecnologica, oportunidades, planejamento, governanca.

### Por que aplicar

- Alinha solucao tecnica com objetivos de negocio.
- Habilita conversa com arquitetos corporativos do cliente.
- Garante que decisoes locais respeitam padroes globais (catalogo de servicos,
  taxonomia de dominios, capacidades de negocio).
- Documenta artefatos em formato reconhecido pela industria.

### Quando aplicar

- Aplicacoes destinadas a integrar com sistema corporativo de medio/grande porte.
- Empresas onde existe time de arquitetura corporativa.
- Projetos com governanca ou auditoria externa.

### Quando NAO aplicar

- Startups iniciais sem time de arquitetura.
- POCs e MVPs (overhead nao se paga).
- Projetos isolados sem integracao corporativa.

### Como o agente aplica

PM Agent ao registrar nova historia:

- Verifica se o produto/feature mapeia para capacidade de negocio existente
  no catalogo corporativo (se houver).
- Marca a historia com a capacidade correspondente.

Architect Agent ao desenhar nova arquitetura:

- Verifica catalogo corporativo de servicos e dominios antes de propor solucao.
- Reusa servicos existentes em vez de criar novos quando aplicavel.
- Documenta solucao em formato compativel com TOGAF (Business / Data /
  Application / Technology architecture).
- Identifica gaps em relacao a arquitetura-alvo corporativa.

### Enforcement

- **Manual review:** Architect Agent valida ADRs contra catalogo corporativo
  do cliente (se existir).
- **Diretriz:** este padrao nao gera enforcement automatico - depende de
  contexto corporativo do cliente.

### Padroes relacionados

- BIAN (TOGAF eh framework geral, BIAN eh especializacao para bancos)
- DDD - Bounded Contexts (contextos podem mapear capacidades TOGAF)

---

## 14. BIAN

**Camada:** Negocio

**Aplicavel a:** PM Agent, Architect Agent (so para dominio bancario)

**Tipo:** Diretriz arquitetural (nao gera codigo diretamente)

### O que e

Banking Industry Architecture Network. Padronizacao internacional de servicos
e dominios de negocio bancario. Define um Service Landscape com 300+ Service
Domains agrupados por categoria (Customer, Channel, Product, Operations, etc).
Cada Service Domain tem definicao formal, Control Records e operacoes padrao.

### Por que aplicar

- Vocabulario padrao reconhecido por bancos globalmente.
- Habilita interoperabilidade - sistemas de bancos diferentes falam mesma lingua.
- Reduz reinvencao - "atendimento ao cliente" tem definicao formal pronta.
- Facilita auditoria e compliance (regulador reconhece taxonomia).

### Quando aplicar

- Aplicacoes para o dominio bancario (banco, fintech, meio de pagamento).
- Integracoes entre sistemas bancarios.
- Sistemas que serao auditados por reguladores financeiros.

### Quando NAO aplicar

- Aplicacoes fora do dominio financeiro.
- Internal tooling sem exposicao a sistemas externos.
- POCs onde mapeamento BIAN ainda nao agrega valor.

### Como o agente aplica

PM Agent ao registrar historia em projeto bancario:

- Identifica qual Service Domain BIAN cobre a historia (ex: "Customer
  Onboarding", "Payment Order").
- Tagga a historia com o Service Domain.
- Usa terminologia BIAN nos titulos e descricoes ("Customer Reference Data
  Management" em vez de "cadastro de cliente").

Architect Agent ao desenhar arquitetura bancaria:

- Mapeia componentes da solucao para Service Domains BIAN.
- Documenta no ADR quais Service Domains sao implementados, consumidos e
  expostos.
- Reusa Control Records BIAN onde aplicavel em vez de inventar estrutura propria.

### Enforcement

- **Manual review:** PM Agent valida tagging BIAN em projetos bancarios.
- **Diretriz:** nao gera enforcement automatico - depende de contexto do projeto.

### Padroes relacionados

- TOGAF (BIAN especializa TOGAF para banking)
- DDD - Bounded Contexts (Service Domain BIAN frequentemente mapeia para
  Bounded Context)

---

## 15. SRE - Site Reliability Engineering

**Camada:** Resiliencia

**Aplicavel a:** Architect Agent, Developer Agent, QA Agent

**Tipo:** Diretriz arquitetural (afeta design e operacao)

### O que e

Disciplina criada pelo Google que aplica engenharia de software a problemas
de operacao. Baseia decisoes em metricas (SLI - Service Level Indicators) e
metas (SLO - Service Level Objectives). Conceito central: error budget - se
o servico estoura SLO, congela features ate recuperar.

### Por que aplicar

- Decisoes de "estavel ou rapido" deixam de ser opiniao - viram dado.
- Times de produto e operacao usam mesma metrica para negociar.
- Investimento em confiabilidade fica proporcional ao impacto real.
- Habilita conversa madura sobre disponibilidade ("99.9% basta para este
  servico" vs "queremos 99.99%").

### Quando aplicar

- Servicos em producao com usuarios reais.
- Sistemas onde indisponibilidade tem custo direto (financeiro, reputacao,
  vidas).

### Quando NAO aplicar

- Scripts internos sem SLA.
- POCs e prototipos.
- Aplicacoes com baseline de uptime aceitavel sem definicao formal.

### Como o agente aplica

Architect Agent ao desenhar servico critico:

- ADR define SLIs (latencia p95, taxa de erro, throughput, disponibilidade).
- ADR define SLOs (metas mensuraveis: "p95 < 300ms em 99% dos requests").
- ADR define error budget (quanto pode estourar antes de freeze de features).
- ADR define alertas: golden signals (latency, traffic, errors, saturation).

Developer Agent ao implementar:

- Instrumenta endpoints com metricas (Prometheus, OpenTelemetry).
- Logs estruturados incluem campos para correlacao (trace_id, span_id).
- Health checks distinguem liveness (estou vivo) e readiness (estou pronto
  pra trafego).

QA Agent ao gerar testes:

- Testes de carga validam SLOs antes do deploy.
- Cenarios incluem degradacao gradual (nao so binario up/down).

### Exemplo correto (ADR de SLO)

```
SLI: latencia p95 do endpoint POST /orders
SLO: p95 < 300ms em 99.5% dos requests, medido em janela de 28 dias
Error budget: 0.5% = 18 minutos por mes acima de 300ms
Acao se estourar: freeze de novas features, foco em performance ate recuperar
Alertas: page on-call se p95 > 500ms por 5 minutos consecutivos
```

### Enforcement

- **Manual review:** Architect Agent valida ADR de servico critico contra
  checklist SRE.
- **Diretriz:** nao gera enforcement automatico de codigo - foca em design,
  ADR e operacao.

### Padroes relacionados

- Circuit Breaker (implementacao concreta de SLO de disponibilidade)
- 12-Factor App (logs como stream eh pre-requisito para SRE)
- Chaos Engineering (validacao ativa de SLOs)

---

## 16. Chaos Engineering

**Camada:** Estresse

**Aplicavel a:** QA Agent, Architect Agent

**Tipo:** Diretriz arquitetural (define pratica, nao gera codigo direto)

### O que e

Pratica de injetar falhas controladas em ambientes pre-producao (e as vezes
producao) para validar que sistemas se recuperam graciosamente. Disciplina
popularizada pelo Netflix com a Simian Army (Chaos Monkey, Chaos Kong).
Hipotese -> experimento -> observacao -> aprendizado.

### Por que aplicar

- Descobre falhas em quiescent state - antes que cliente descubra em producao.
- Valida assumptions de resiliencia ("circuit breaker funciona" so e verdade
  se foi testado).
- Constroi cultura de "falha eh inevitavel, recuperacao precisa ser planejada".
- Reduz panico em incidente real - time ja viveu a falha em ambiente seguro.

### Quando aplicar

- Servicos criticos com SLO definido (combina com SRE).
- Sistemas distribuidos onde falha de um componente nao deve derrubar tudo.
- Aplicacoes com dependencias externas multiplas.

### Quando NAO aplicar

- Servicos sem SLO definido (nao tem como medir se chaos quebrou).
- Sistemas em fase muito inicial sem testes basicos cobrindo happy path.
- Producao sem cobertura de monitoramento adequada.

### Como o agente aplica

QA Agent ao planejar testes de feature critica:

- Identifica dependencias externas (banco, cache, fila, APIs).
- Gera cenarios de chaos: latencia adicionada, conexao dropada, resposta
  lenta, erro 500 intermitente.
- Cenarios usam @pytest.mark.chaos e rodam separados da suite normal.

Architect Agent ao desenhar servico critico:

- ADR documenta hipoteses de resiliencia ("se cache falhar, degradamos para
  banco direto").
- ADR define experimentos de chaos para validar cada hipotese.
- Define ferramenta de chaos a ser usada (toxiproxy, gremlin, chaos mesh,
  litmus).

### Exemplo correto (cenario de chaos)

```python
import pytest
from toxiproxy import Toxiproxy

@pytest.mark.chaos
async def test_endpoint_funciona_com_redis_lento():
    toxiproxy = Toxiproxy()
    proxy = toxiproxy.create("redis_proxy", upstream="redis:6379")
    proxy.add_toxic("latency", attributes={"latency": 2000})

    response = await client.get("/produtos/123")

    assert response.status_code == 200
    assert response.elapsed.total_seconds() < 3.0
```

### Enforcement

- **Manual review:** Architect Agent valida cobertura de chaos para servicos
  criticos.
- **Diretriz:** nao gera enforcement automatico de codigo - foca em pratica
  e documentacao.

### Padroes relacionados

- SRE (chaos valida SLOs ativamente)
- Circuit Breaker (chaos confirma que breaker funciona)
- Saga Pattern (chaos valida compensacoes em saga)

---

## Fim da Parte A

Parte A documenta 16 padroes classicos de fundamentos de software (12
operacionalizaveis + 4 diretrizes arquiteturais). Cobre: Estrutura, Qualidade,
Validacao, Dominio, Requisitos, Contratos, Operacao, Resiliencia, Consistencia,
Seguranca, Rastreabilidade, Cognicao, Estrategia, Negocio, Confiabilidade,
Estresse.

Proximas partes:
- Parte B - Padroes Agenticos Modernos (10 padroes especificos de sistemas LLM)
- Parte C - Stack-Dependent (14 padroes condicionais)

