# EDA/jupia_bacia

Objetivo: construir um novo relatorio no mesmo padrao visual e analitico das
entregas do Tiete e de Clarks Hill, mas com recorte proprio para a bacia
hidrografica contribuinte de Jupia.

## Pergunta operacional

O pedido recebido foi: produzir um relatorio dedicado a Jupia porque a bacia
hidrografica associada ao reservatorio agrega grandes contribuintes e mais
estacoes, especialmente os rios Paranaiba, Grande e Tiete. A leitura correta e
que Jupia nao deve ser tratado apenas como um ponto final da cascata do Tiete,
mas como um no integrador do sistema Alto Parana.

## Recorte atual

Esta versao combina:

- `data/raw/operacao_reservatorio/ons_hidro_2000.parquet` a
  `data/raw/operacao_reservatorio/ons_hidro_2025.parquet`
- rodada de descoberta Perplexity:
  `data/runs/perplexity-intel-58d59340/`
- coleta operacional:
  `data/runs/operational-collect-jupia-20260607-225450/`

Camadas materializadas:

- Rio Grande
- Rio Paranaiba
- Rio Tiete
- Rio Parana / no Jupia
- inventario ANA/Hidro para UHE Jupia, Rio Sucuriu e UHE Jupia Sucuriu
- series convencionais ANA/GitHub quando disponiveis
- documentos brutos de qualidade da agua, saneamento/poluicao e bacias

O termo "UHE JUPIA SUCURIU" foi preservado como demanda e localizado no
inventario ANA/Hidro. A coleta encontrou matches diretos:

- `1952023` - UHE JUPIA RIO SUCURIU
- `63001850` - UHE JUPIA RIO SUCURIU, Rio Sucuriu
- `63003300` - UHE JUPIA SUCURIU, Rio Parana

Nos dados ONS locais, a serie operacional continua aparecendo como `JUPIA` na
bacia `PARANA`. O codigo ANA `63003300` foi encontrado no inventario, mas nao
teve CSV historico disponivel no branch `dev` do repositorio ANA baixado nesta
rodada. Essa diferenca fica registrada como lacuna de disponibilidade, nao como
ausencia da estacao.

## Saidas

- `data/staging/jupia_bacia/ons_jupia_contributing_system_daily.csv`
- `data/analytic/jupia_bacia/jupia_system_monthly.csv`
- `data/analytic/jupia_bacia/jupia_system_annual.csv`
- `data/analytic/jupia_bacia/jupia_coverage_matrix.csv`
- `data/staging/jupia_bacia/ana_jupia_station_inventory_matches.csv`
- `data/staging/jupia_bacia/ana_jupia_station_series_coverage.csv`
- `data/analytic/jupia_bacia/jupia_requested_station_matches.csv`
- `data/analytic/jupia_bacia/jupia_station_series_coverage_summary.csv`
- `eda/jupia_bacia/figures/*.svg`
- `eda/jupia_bacia/report_context.json`
- `docs/jupia/index.html`

## Regras

- Nao misturar coleta bruta com staging/analytic.
- Nao fabricar dados de Sucuriu se a fonte local nao trouxer esse identificador.
- Preservar Jupia como no integrador do sistema, nao como simples extensao do
  relatorio do Tiete.
- Usar Paranaiba, Grande e Tiete como camadas contribuintes principais.
- Declarar lacunas de cobertura e continuidade de coleta no HTML.
