# Research Harness Principles

Este documento registra a essencia arquitetural extraida do repositorio
`Research_FREnTE` para orientar a criacao de um novo repositorio generico:
um harness de pesquisa capaz de receber qualquer contexto, descobrir fontes,
coletar dados, tratar artefatos, produzir EDA e gerar narrativas auditaveis.

O repositorio atual deve continuar como implementacao operacional do Projeto
100K. O novo repositorio deve nascer como generalizacao dos seus principios,
sem quebrar nem diluir o valor pratico que este projeto ja entrega.

## 1. Tese central

O sistema nao e apenas um pipeline de busca, nem apenas uma automacao de
relatorios. A essencia e:

> dado um contexto analitico ou cientifico, transformar intencao em trilhas de
> busca, trilhas em fontes, fontes em alvos coletaveis, alvos em dados
> organizados, dados em EDA, e EDA em narrativa auditavel.

O harness generico deve preservar esse encadeamento, mas tornar seus contratos
executaveis, versionados e independentes de um dominio especifico.

## 2. O que o repositorio atual prova

`Research_FREnTE` ja demonstra uma arquitetura viavel para pesquisa multi-agente:

- recebe contexto mestre em `config/context_*.yaml`;
- recebe trilhas tematicas em `config/tracks_*.yaml`;
- executa descoberta API-first via Perplexity;
- persiste coleta crua antes de qualquer interpretacao;
- filtra e valida fontes;
- enriquece metadados sem permitir que a LLM invente a estrutura do dominio;
- ranqueia acesso e prioridade;
- prepara handoffs para coleta operacional;
- coleta bruto em `data/runs/{run-id}/collection/`;
- transforma dados em `data/staging/` e `data/analytic/`;
- gera EDA e figuras;
- fecha narrativas em HTML preservando padrao visual.

Esse desenho e forte porque separa intencao, descoberta, coleta, tratamento,
analise e comunicacao. O novo harness deve preservar essa separacao como regra
fundacional.

## 3. Definicao de harness neste contexto

Neste projeto, "harness" significa uma estrutura que:

- padroniza inputs;
- orquestra agentes e adapters;
- registra cada etapa como artefato;
- valida contratos entre etapas;
- permite repetir, auditar e comparar execucoes;
- aprende com execucoes anteriores;
- preserva lacunas, bloqueios e incertezas como informacao de primeira classe;
- permite trocar dominios, fontes, modelos e ferramentas sem reescrever o fluxo.

O harness nao deve ser apenas um nome para o pipeline. Ele deve ser o conjunto
de contratos que impede que um novo contexto quebre a estabilidade interna.

## 4. Separacao entre os dois repositorios

### 4.1 Research_FREnTE atual

Papel:

- implementacao concreta do Projeto 100K;
- dominio ambiental, hidrologico, sedimentologico e de reservatorios;
- operacao real para Tiete, Jupia, Savannah River e Clarks Hill;
- laboratorio vivo para validar padroes, agentes, EDA e relatorios.

Regra:

- nao transformar este repositorio em framework generico a ponto de prejudicar
  sua utilidade operacional;
- melhorar contratos e documentacao aqui apenas quando isso fortalecer o uso
  real do Projeto 100K.

### 4.2 Novo repositorio

Papel:

- harness generico de pesquisa contextual;
- qualquer dominio entra por configuracao e contratos;
- ferramentas externas entram por adapters;
- agentes entram por funcoes estaveis;
- memoria e aprendizado entram como parte do mecanismo operacional.

Regra:

- copiar principios, nao acoplamentos de dominio;
- usar este repositorio como caso fundador, nao como molde rigido.

## 5. Principios arquiteturais que devem ser preservados

### 5.1 O contexto manda no pipeline

Toda execucao deve comecar por um contexto explicito:

- objetivo analitico;
- recorte espacial, temporal ou institucional;
- pergunta principal;
- dominios tematicos;
- fontes preferenciais;
- exclusoes;
- outputs esperados;
- criterios de sucesso.

O harness nao deve buscar "dados sobre X" de forma generica. Ele deve buscar
fontes que respondam ao contexto recebido.

### 5.2 Busca e guiada por trilhas

As trilhas sao a decomposicao operacional do contexto. Elas devem informar:

- `research_track`;
- pergunta da trilha;
- intencao;
- prioridade;
- fontes-alvo;
- parametros desejados;
- janela temporal alvo;
- formato esperado;
- dominio ou camada analitica.

No repositorio atual, parte da semantica vem do prefixo da trilha. No harness
generico, essa semantica deve ser declarada de forma explicita no YAML de
configuracao.

### 5.3 Coleta bruta antes de interpretacao

Nenhum dado deve entrar diretamente em `staging` ou `analytic` sem antes ter
sido registrado como bruto ou como artefato de origem.

Regra permanente:

```text
external source -> raw/run artifact -> staging -> analytic -> EDA -> report
```

O harness deve sempre conseguir responder:

- de onde veio este dado?
- quando foi coletado?
- por qual metodo?
- qual URL, endpoint, arquivo ou portal originou o artefato?
- houve bloqueio, parcialidade ou perda de cobertura?

### 5.4 LLM extrai, mas nao funda a verdade

A LLM pode:

- resumir;
- extrair metadados;
- propor classificacoes auxiliares;
- estruturar guias;
- ajudar a escrever narrativa.

A LLM nao deve:

- inventar cobertura temporal;
- fabricar parametros;
- promover hipotese a fato;
- decidir sozinha a ontologia do dominio;
- substituir validacao de schema;
- apagar lacunas.

No harness generico, cada campo extraido por LLM deve carregar metodo,
confianca operacional ou status de revisao.

### 5.5 Handoff e um contrato, nao uma conversa

Cada passagem entre agentes deve produzir um artefato validavel.

Exemplos:

```text
Discovery -> Harvester:
  handoff.json
  harvester_targets.csv

Harvester -> Analyst:
  manifest.json
  collection inventory
  schema hints
  join keys
  coverage matrix

Analyst -> Narrator:
  report_context.json
  figures/
  analytic tables
  data gaps
```

O proximo agente so deve avancar quando o contrato minimo da etapa anterior
estiver completo ou quando a incompletude estiver explicitamente registrada.

### 5.6 Lacunas sao produto do sistema

Um bom harness nao apenas entrega dados. Ele tambem entrega:

- lacunas;
- bloqueios;
- cobertura insuficiente;
- assimetrias entre regioes, fontes ou variaveis;
- alvos que precisam de coleta futura;
- diferenca entre janela desejada e janela retornada.

No caso Clarks Hill, por exemplo, o alvo de 20 anos e uma regra analitica. Se a
fonte retorna menos, a defasagem precisa aparecer no manifesto, no EDA e no
relatorio. O novo harness deve permitir esse tipo de contrato em qualquer
dominio.

### 5.7 EDA serve a pergunta, nao ao grafico

O EDA nao deve gerar graficos genericos. Cada figura deve existir para explicar
uma parte da pergunta.

Para qualquer dominio, a camada EDA deve declarar:

- qual pergunta a figura responde;
- quais dados sustentam a figura;
- qual cobertura real existe;
- qual juncao foi usada;
- quais limites interpretativos permanecem.

### 5.8 Relatorio consome contexto estruturado

O HTML ou relatorio final nao deve reprocessar dados silenciosamente. Ele deve
consumir:

- figuras finais;
- metricas ja calculadas;
- `report_context.json`;
- fontes;
- lacunas;
- notas metodologicas.

O renderizador deve ser substituivel. A estrutura narrativa deve ser produto do
contrato analitico.

## 6. Camadas recomendadas para o novo harness

```text
Domain Context
  -> Track Planner
  -> Search / Discovery Adapter
  -> Filter + Validate
  -> Semantic Enrichment
  -> Access Ranking
  -> Handoff Builder
  -> Operational Collection
  -> Raw Artifact Store
  -> Staging Builder
  -> Analytic Builder
  -> EDA Generator
  -> Report Context Builder
  -> Renderer
  -> Learning + Memory Update
```

Cada camada deve ser pequena, testavel e persistente.

## 7. Estrutura de diretorios sugerida para o novo repositorio

```text
research-harness/
|-- contexts/
|   |-- examples/
|   `-- schemas/
|-- contracts/
|   |-- domain.schema.json
|   |-- tracks.schema.json
|   |-- handoff.schema.json
|   |-- manifest.schema.json
|   |-- staging.schema.json
|   `-- report_context.schema.json
|-- runs/
|   `-- {run-id}/
|       |-- inputs/
|       |-- discovery/
|       |-- validation/
|       |-- enrichment/
|       |-- handoff/
|       |-- collection/
|       |-- staging/
|       |-- analytic/
|       |-- reports/
|       `-- manifest.json
|-- src/
|   |-- harness/
|   |   |-- orchestrator.py
|   |   |-- artifact_store.py
|   |   |-- contracts.py
|   |   |-- validators.py
|   |   `-- run_state.py
|   |-- agents/
|   |-- adapters/
|   |   |-- search/
|   |   |-- llm/
|   |   |-- browser/
|   |   |-- collectors/
|   |   `-- renderers/
|   |-- skills/
|   `-- cli.py
|-- skills/
|-- prompts/
|-- docs/
|-- tests/
`-- README.md
```

## 8. Contratos minimos

### 8.1 Domain context

Campos recomendados:

```yaml
domain_id: string
domain_name: string
objective: string
primary_question: string
geographic_scope: []
temporal_scope:
  target_start: string
  target_end: string
  target_years: integer
thematic_axes: []
preferred_sources: []
exclusions: []
expected_outputs: []
success_criteria: []
```

### 8.2 Track

Campos recomendados:

```yaml
research_track: string
chat_label: string
priority: high | medium | low
target_intent: dataset_discovery | contextual_intelligence | academic_knowledge
domain_layer: string
hierarchy_level: macro | meso | bridge | micro | custom
thematic_axis: string
research_question: string
task_prompt: string
source_hints: []
expected_formats: []
target_parameters: []
coverage_target:
  years: integer
  required: boolean
```

### 8.3 Run manifest

Campos recomendados:

```json
{
  "schema_version": "1.0",
  "run_id": "",
  "pipeline_name": "",
  "domain_id": "",
  "stage": "",
  "status": "",
  "generated_at": "",
  "inputs": {},
  "outputs": {},
  "artifacts": [],
  "counts": {},
  "coverage": {},
  "blockers": [],
  "warnings": [],
  "parent_run_id": null
}
```

### 8.4 Handoff

Campos recomendados:

```json
{
  "handoff_id": "",
  "from_stage": "discovery",
  "to_stage": "collection",
  "domain_id": "",
  "targets": [],
  "required_fields": [],
  "coverage_contract": {},
  "known_gaps": [],
  "ready_count": 0,
  "needs_review_count": 0
}
```

Cada target deve carregar, no minimo:

- rank;
- fonte;
- URL inicial;
- dominio;
- camada analitica;
- prioridade;
- tipo de acesso;
- formato esperado;
- periodo esperado;
- parametros;
- metodo de coleta sugerido;
- status de revisao.

### 8.5 Staging e analytic contracts

Cada dataset harmonizado deve declarar:

- caminho;
- fonte;
- schema;
- chave temporal;
- chave espacial;
- unidade;
- granularidade;
- periodo real;
- periodo alvo;
- lacunas;
- regras de limpeza;
- relacao com artefatos brutos.

## 9. Papel do Hermes no novo harness

O novo repositorio deve considerar Hermes como pilar para aprendizado,
memoria procedural e continuidade operacional.

Segundo a documentacao do Hermes, os elementos mais relevantes para este desenho
sao:

- memoria persistente e curada entre sessoes;
- skills como documentos de conhecimento carregados sob demanda;
- context files, especialmente `AGENTS.md`, para instrucoes de projeto;
- session storage com busca para recuperacao de conversas;
- tool registry e backends de execucao;
- suporte a MCP e subagentes;
- capacidade de o agente criar ou melhorar skills a partir da experiencia.

No harness, Hermes deve ser usado para tres funcoes complementares.

### 9.1 Memoria operacional

Guardar aprendizados curtos e duraveis:

- quais fontes funcionaram;
- quais portais bloquearam;
- quais endpoints foram estaveis;
- quais convenções do projeto importam;
- quais estrategias de coleta deram certo;
- quais erros devem ser evitados.

Memoria nao deve guardar:

- dumps de dados;
- arquivos grandes;
- credenciais;
- conclusoes nao verificadas;
- conteudo que ja esta em contrato versionado no repo.

### 9.2 Skills como memoria procedural

Cada fluxo repetivel deve virar skill:

- descoberta API-first;
- coleta portal-first;
- construcao de handoff;
- validacao de run;
- EDA por dominio;
- geracao de relatorio;
- tratamento de bloqueios;
- auditoria de cobertura.

O repositorio deve manter skills versionadas quando forem parte do metodo
cientifico ou operacional. Skills pessoais do agente podem viver no ambiente
Hermes, mas os workflows essenciais devem ser promovidos ao repo.

### 9.3 Context files como contrato de colaboracao

`AGENTS.md` deve continuar sendo o arquivo que explica:

- objetivo do repositorio;
- arquitetura;
- camadas;
- regras de desenvolvimento;
- regras de dados;
- convencoes de saida;
- limites do agente.

No novo harness, contextos locais por subdiretorio podem ser usados para evitar
que um agente carregue instrucoes irrelevantes antes da hora.

## 10. Como o harness deve aprender

O aprendizado deve ter dois destinos diferentes:

### 10.1 Aprendizado local do run

Vai para artefatos versionados:

- manifest;
- notes;
- handoff;
- blocked notes;
- coverage matrix;
- source inventory;
- report context.

Esse aprendizado pertence ao projeto e deve ser reprodutivel.

### 10.2 Aprendizado do agente

Vai para Hermes memory ou skills:

- heuristicas que melhoram proximas execucoes;
- preferencias operacionais;
- padroes recorrentes de fontes;
- estrategias de navegacao;
- decisoes de design do harness.

Esse aprendizado ajuda o agente a trabalhar melhor, mas nao substitui os
artefatos auditaveis do repo.

## 11. Interfaces substituiveis

O harness deve depender de interfaces, nao de fornecedores fixos.

Exemplos:

```text
SearchAdapter:
  Perplexity
  web search
  scholarly APIs
  domain-specific catalogs

LLMAdapter:
  OpenAI
  Hermes-selected model
  local model
  provider via OpenRouter or Nous Portal

BrowserAdapter:
  Playwright
  Hermes browser tools
  HTTP-only fallback

CollectionAdapter:
  direct download
  API
  portal
  WFS/WMS
  PDF extraction

RendererAdapter:
  HTML
  Markdown
  dashboard
  slide deck
```

O contrato da etapa deve ser mais estavel que a ferramenta usada para executa-la.

## 12. Critérios de passagem entre etapas

Cada etapa deve ter uma politica de completude.

Exemplo:

```text
Discovery completa quando:
  - manifest existe
  - raw sessions existem
  - ranked datasets existem
  - contagem > 0 ou zero-result foi explicitamente aceito

Handoff completo quando:
  - targets tem URL inicial
  - source_slug existe
  - access_type existe
  - needs_review esta marcado quando aplicavel

Collection completa quando:
  - cada target tem status collected, partial, blocked ou error
  - bruto esta salvo
  - manifest registra metodo, URL e bloqueios

EDA completa quando:
  - staging e analytic foram gerados ou lacunas foram declaradas
  - figuras possuem fonte e pergunta
  - report_context existe

Report completo quando:
  - narrativa usa apenas dados disponiveis
  - lacunas permanecem visiveis
  - fontes e artefatos estao rastreaveis
```

## 13. O que deve ser dominio-especifico

Deve ficar em configuracao ou pacote de dominio:

- contexto mestre;
- trilhas;
- taxonomia;
- fontes preferenciais;
- parametros;
- unidades;
- janelas temporais;
- criterios de cobertura;
- chaves de juncao;
- templates narrativos especificos.

## 14. O que deve ser generico

Deve ficar no core do harness:

- orquestracao;
- armazenamento de artefatos;
- manifestos;
- validadores;
- adapters;
- retry e erro;
- politicas de bloqueio;
- schemas de handoff;
- CLI;
- logs;
- relatorio de completude.

## 15. Licoes especificas do Research_FREnTE

### 15.1 River-first e sedimentocentrico

No eixo Clarks Hill, a regra mais importante e que o rio Savannah e o
protagonista contextual, enquanto Hartwell, Russell e Thurmond sao estruturas
explicativas. A interpretacao final e sedimentologica.

Licao generica:

> o harness deve preservar a pergunta principal do dominio, mesmo quando dados
> secundarios forem mais faceis de coletar.

### 15.2 Tiete como padrao de EDA contextual

O eixo Tiete mostra como combinar operacao, hidrologia, pressao ambiental e
narrativa visual.

Licao generica:

> um dominio pode fornecer um padrao visual e metodologico sem obrigar outros
> dominios a copiar suas variaveis.

### 15.3 Firecrawl e opcional

No fluxo atual, Firecrawl gera guias de coleta, mas a rodada Savannah usa
frequentemente `--skip-collection-guides`.

Licao generica:

> recursos caros ou opcionais devem ser adapters substituiveis, nunca
> dependencias obrigatorias do harness.

### 15.4 Relevance score foi removido

O fluxo atual evita `relevance_score`; relevancia vem do desenho das trilhas, da
prioridade e do ranking operacional.

Licao generica:

> evitar scores opacos quando a prioridade pode ser expressa por contrato,
> contexto e camada analitica.

## 16. Roadmap recomendado para o novo repo

### Fase 1 - Extrair o nucleo

- definir schemas de `domain_context`, `tracks`, `manifest` e `handoff`;
- implementar `ArtifactStore`;
- implementar `RunState`;
- implementar CLI minima;
- portar o fluxo discovery -> filter -> enrich -> rank -> handoff.

### Fase 2 - Formalizar coleta

- criar interfaces de collector;
- implementar direto HTTP, portal/manual note e API;
- registrar bloqueios;
- validar `collection manifest`.

### Fase 3 - Formalizar staging e analytic

- criar contratos de dataset;
- criar validadores de schema;
- criar matriz de cobertura;
- criar registry de join keys.

### Fase 4 - Relatorio e EDA

- gerar `report_context.json`;
- criar renderizadores substituiveis;
- manter HTML como uma saida, nao como centro do sistema.

### Fase 5 - Hermes learning loop

- definir quais aprendizados viram memoria;
- definir quais aprendizados viram skills;
- criar skills iniciais do harness;
- testar recuperacao de aprendizados entre execucoes.

## 17. Regra final

O harness deve ser generico, mas nao generico demais.

Ele deve receber qualquer contexto, mas sempre exigir:

- pergunta clara;
- trilhas declaradas;
- artefatos persistidos;
- contratos validaveis;
- separacao entre bruto, tratado, analitico e narrativo;
- lacunas explicitas;
- aprendizado preservado.

Se esses principios forem mantidos, o novo repositorio podera escalar para
outros dominios sem perder a disciplina metodologica que tornou o
`Research_FREnTE` funcional.

## 18. Referencias externas para o desenho Hermes

- Hermes Agent documentation: https://hermes-agent.nousresearch.com/docs/
- Persistent Memory: https://hermes-agent.nousresearch.com/docs/user-guide/features/memory
- Skills System: https://hermes-agent.nousresearch.com/docs/user-guide/features/skills
- Context Files: https://hermes-agent.nousresearch.com/docs/user-guide/features/context-files
- Architecture: https://hermes-agent.nousresearch.com/docs/developer-guide/architecture
