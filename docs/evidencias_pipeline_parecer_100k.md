# Evidências do pipeline multiagente para o parecer do Projeto 100K

Inventário local em 14 de outubro de 2026. Este pacote reúne três execuções já existentes; nenhuma busca externa foi feita para prepará-lo. O escopo é o item 2 do parecer, exceto a contagem de fontes aprovadas por revisão humana.

## O que os arquivos demonstram

O [pipeline](../src/pipelines/perplexity_intelligence_pipeline.py) executa `FilterValidateAgent`, `EnrichAgent`, `RankAccessAgent` e `ReportAgent` em sequência. Cada agente lê um dicionário `context`, devolve `updates`, e o pipeline incorpora essas atualizações ao mesmo contexto antes do agente seguinte. Os arquivos em `processing/` são registros persistidos das saídas das três primeiras etapas. Portanto, há evidência da passagem de dados entre etapas, mas não um log de mensagens ou diálogo entre agentes.

```text
plano de buscas -> raw-sessions.json -> FilterValidateAgent
  -> 01-filtered-sources.json -> EnrichAgent
  -> 02-enriched-datasets.json -> RankAccessAgent
  -> 03-ranked-datasets.json -> ReportAgent -> relatório
```

Em cada diretório de execução incluímos `manifest.json`, `config/context.json`, `config/tracks.json`, `search-plan.json`, `collection/raw-sessions.json`, os três JSONs de `processing/` e o relatório Markdown em `reports/{run-id}.md`. O contexto, as trilhas e o plano preservam as entradas exatas da rodada; os cinco arquivos citados pelo colaborador permitem auditar coleta e processamento, e o Markdown comprova a geração do relatório final.

## Rodadas selecionadas para conferência

| Caso | Rodada | Justificativa | Links retornados | Duplicatas removidas | Fontes após filtro | Fontes no ranking | Enriquecimento pela LLM | Extração heurística após erro |
|---|---|---|---:|---:|---:|---:|---:|---:|
| Rio Tietê | [perplexity-intel-8b5a5553](../data/runs/perplexity-intel-8b5a5553/manifest.json) | Rodada ampla de 12 buscas do recorte Tietê; amostra demonstrativa, sem vínculo identificado com uma versão específica do dashboard. | 240 | 13 | 227 | 20 | 226 | 1 |
| Clarks Hill / Savannah | [perplexity-intel-5fdaad57](../data/runs/perplexity-intel-5fdaad57/manifest.json) | Rodada apontada como busca concluída no [README da EDA](../eda/clarks_hill/README.md). | 180 | 22 | 158 | 30 | 158 | 0 |
| Jupiá | [perplexity-intel-58d59340](../data/runs/perplexity-intel-58d59340/manifest.json) | Rodada citada no [README da EDA](../eda/jupia_bacia/README.md) e usada pelo coletor operacional. | 200 | 25 | 175 | 80 | 175 | 0 |

As contagens do `manifest.json` foram conferidas contra o número de sessões e links em `raw-sessions.json` e o tamanho das listas nos três arquivos de `processing/`. Nas três rodadas, os totais coincidem.

O identificador do modelo de enriquecimento nessas execuções é **OpenAI `gpt-4.1-nano`**, registrado em `llm_model` e `enrich_meta.model`. `enrich_meta.llm_count` demonstra quantas extrações pela LLM terminaram com sucesso. Os arquivos não fixam uma revisão datada do modelo. Não se deve atribuir automaticamente ao `ReportAgent` o mesmo modo de execução apenas a partir dessas contagens: seu `report_meta` não é gravado no `manifest.json`.

Na rodada do Tietê, `enrich_meta.error_count=1`, `heuristic_count=1` e `execution_mode=hybrid`. O respectivo item em `02-enriched-datasets.json` tem `enrichment_method=heuristic`, sem cobertura temporal ou espacial e sem parâmetros extraídos. Isso comprova um acionamento do caminho de contingência do **enriquecimento de metadados**. A mesma rodada registra 163 fallbacks de **guia de coleta** via Firecrawl; são outro mecanismo e não devem ser somados ao erro da LLM. Rodadas com `llm_mode=off` usam heurística por configuração, não por falha; não foram usadas nesta tabela.

## Como interpretar as contagens

- **Links retornados**: soma dos links nas sessões de busca, incluindo repetidos. Não representa fontes únicas.
- **Duplicatas removidas**: URLs repetidas após a normalização do `FilterValidateAgent`.
- **Fontes após filtro**: fontes mantidas. Snippets curtos são sinalizados com `needs_review`; o filtro não os remove por esse motivo.
- **Fontes no ranking**: lista ordenada e limitada por configuração. Não representa validação científica nem aprovação humana.
- **Aprovação humana**: conforme o relato do pesquisador, fontes consideradas relevantes foram promovidas manualmente à lista de fontes preferenciais entre rodadas. Os JSONs não registram a decisão individual nem permitem uma contagem auditável de aprovadas.

Essas são rodadas individuais selecionadas para verificar o funcionamento. Há outras rodadas, especialmente para Savannah. Não se deve somá-las ou apresentar a tabela como total definitivo de cada estudo de caso sem antes fixar quais execuções compõem o recorte do artigo e identificar sobreposições.
