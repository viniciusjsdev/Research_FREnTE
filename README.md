# Research_FREnTE

Pipeline multi-agente para descoberta de fontes ambientais via **Perplexity Search API**, enriquecimento por LLM e ranking de acesso. Desenvolvido no âmbito do **Projeto 100K** — pesquisa comparativa internacional sobre dinâmica de matéria orgânica e sedimentos em reservatórios.

O Projeto 100K possui dois eixos geográficos:

- **Brasil — Bacia do Rio Tietê:** impactos antrópicos na dinâmica do material orgânico nos reservatórios em cascata (São Paulo → Três Lagoas / Jupiá).
- **EUA — Clarks Hill Lake:** caracterização hidrológica e sedimentológica do Reservatório J. Strom Thurmond (Rio Savannah, GA–SC), com foco no acoplamento ferro–carbono orgânico em sedimentos de fundo — apresentado na GSA 2026 Triple Joint Section Meeting.

## Estrutura

```
Research_FREnTE/
├── src/                              # Pipeline de descoberta + coleta
│   ├── main.py                       # CLI principal
│   ├── agents/                       # FilterValidate, Enrich, RankAccess, Report
│   ├── connectors/                   # Perplexity API, LLM (OpenAI), Firecrawl, CSV
│   ├── pipelines/                    # perplexity_intelligence, operational_collection
│   ├── schemas/                      # Modelos Pydantic (records + settings)
│   ├── generators/                   # HTML report generator
│   ├── assets/                       # Logos (100K, GSU, SENAI)
│   └── utils/                        # Helpers
├── eda/                              # Analises exploratorias
│   └── operacao_reservatorio/        # Reservatorios em cascata (ONS)
│       ├── generate_figures.py       # fig1-5 (volume, vazao, TR, correlacao, anomalia)
│       ├── process_pressoes_ambientais.py  # fig6-8 (queimadas, esgoto, residuos)
│       ├── generate_presentation.py  # HTML builder
│       └── figures/                  # 8 PNGs gerados
├── config/                           # context_100k.yaml + tracks_100k.yaml
├── prompts/                          # YAML de orientacao semantica dos agentes
├── data/
│   ├── staging/                      # Parquets por tema (reservatorio, queimadas, snis, residuos)
│   └── analytic/                     # Parquets derivados (reservatorio_ano)
├── tests/                            # pytest
├── docs/index.html                   # GitHub Pages — apresentacao
├── reports/                          # Auditorias de coleta
├── pyproject.toml
├── requirements.txt
├── .env.example
└── .gitignore
```

## Fluxo principal

1. **CLI** (`src/main.py`) recebe query, contexto e trilhas tematicas
2. **Pipeline** (`src/pipelines/perplexity_intelligence_pipeline.py`) monta contexto mestre e plano de buscas
3. **Coleta** (`src/connectors/perplexity_api.py`) executa buscas via Perplexity Search API
4. **FilterValidateAgent** remove duplicatas e URLs invalidas; herda metadados do track
5. **EnrichAgent** classifica por hierarquia/eixo (deterministico) + extrai metadados via LLM + gera collection guides via Firecrawl
6. **RankAccessAgent** ordena por prioridade/formato e classifica tipo de acesso
7. **ReportAgent** gera relatorio analitico com cobertura, lacunas e proximos passos

## Uso rapido

```bash
# Projeto 100K — Rio Tietê (Brasil)
python -m src.main run \
  --query "impacto antropico materia organica reservatorios cascata tiete sao paulo tres lagoas" \
  --context-file config/context_100k.yaml \
  --tracks-file config/tracks_100k.yaml \
  --max-searches 12 --limit 40 --llm-mode auto

# Clarks Hill Lake (EUA)
python -m src.main run \
  --query "Clarks Hill Lake reservoir characterization hydrology water quality" \
  --context-file config/context_clarkshill.yaml \
  --tracks-file config/tracks_clarkshill.yaml \
  --max-searches 9 --limit 30 --llm-mode auto --skip-collection-guides

# Exportar catalogo
python -m src.main export --catalog data/runs/.../reports/datasets.csv --output saida.csv
```

## Saidas HTML

O projeto gera tres tipos de HTML:

### 1. Dashboard do pipeline (`src/generators/html_report_generator.py`)

Gerado automaticamente ao final de cada execucao do pipeline. Fica em `data/runs/{run-id}/reports/`.
Contem o catalogo de fontes e datasets rankeados, com logos embedados em base64 (sem dependencia de servidor).

### 2. Apresentacoes EDA

#### Rio Tietê — Operacao de Reservatorios (`eda/operacao_reservatorio/`)

Dashboard visual das 8 figuras da analise exploratoria dos reservatorios do Tiete.

```bash
python eda/operacao_reservatorio/generate_figures.py
python eda/operacao_reservatorio/process_pressoes_ambientais.py
python eda/operacao_reservatorio/generate_presentation.py
# Saida: eda/operacao_reservatorio/apresentacao_reservatorios.html
```

#### Clarks Hill Lake (`eda/clarks_hill/`) — em desenvolvimento

Analise exploratoria do reservatorio J. Strom Thurmond (Rio Savannah, GA-SC, EUA).
Foco: caracterizacao hidrologica para contextualizacao da analise de sedimentos de fundo.

### 3. GitHub Pages

Apresentacoes publicas. Self-contained (sem dependencias externas em runtime).

| Estudo | URL | Status |
|--------|-----|--------|
| Rio Tietê (100K) | https://viniciusjsdev.github.io/Research_FREnTE/ | Publicado |
| Clarks Hill Lake | https://viniciusjsdev.github.io/Research_FREnTE/clarks-hill/ | Em desenvolvimento |

```bash
python -m http.server 8000
# Tietê:       http://localhost:8000/docs/index.html
# Clarks Hill: http://localhost:8000/docs/clarks-hill/index.html
```

## Variaveis de ambiente

```env
PERPLEXITY_API_KEY=       # obrigatoria
OPENAI_API_KEY=           # opcional (enriquecimento LLM)
FIRECRAWL_API_KEY=        # opcional (collection guides — usado apenas no contexto Tietê/100K)
```

## Dependencias

`pydantic`, `httpx`, `PyYAML`, `python-dotenv`, `openai`

Para EDA: `pandas`, `matplotlib`, `numpy`, `requests`

## Testes

```bash
python -m pytest tests/ -v
```
