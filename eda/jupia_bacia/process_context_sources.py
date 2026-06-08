"""Prepare staging and analytic tables for the Jupia contributing basin report."""

from __future__ import annotations

import json
import unicodedata
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[2]
RAW_DIR = ROOT / "data" / "raw" / "operacao_reservatorio"
STAGING_DIR = ROOT / "data" / "staging" / "jupia_bacia"
ANALYTIC_DIR = ROOT / "data" / "analytic" / "jupia_bacia"
CONTEXT_PATH = Path(__file__).resolve().parent / "report_context.json"
COLLECTION_RUN_PATTERN = "operational-collect-jupia-*"

TARGET_BASINS = {"GRANDE", "PARANAIBA", "TIETE", "PARANA"}
CORE_RESERVOIRS = {
    "GRANDE": {
        "A. VERMELHA",
        "MARIMBONDO",
        "FURNAS",
        "P. COLOMBIA",
        "L. C. BARRETO",
        "IGARAPAVA",
        "VOLTA GRANDE",
    },
    "PARANAIBA": {
        "EMBORCACAO",
        "NOVA PONTE",
        "ITUMBIARA",
        "SAO SIMAO",
        "C. DOURADA",
        "MIRANDA",
        "BATALHA",
        "CORUMBA",
        "CORUMBA-3",
        "CORUMBA-4",
    },
    "TIETE": {
        "B. BONITA",
        "BARIRI",
        "IBITINGA",
        "PROMISSAO",
        "N. AVANHANDAVA",
        "TRES IRMAOS",
    },
    "PARANA": {
        "JUPIA",
        "I. SOLTEIRA",
        "ILHA + T. IRMAOS",
        "PORTO PRIMAVERA",
    },
}

DISPLAY_BASIN = {
    "GRANDE": "Rio Grande",
    "PARANAIBA": "Rio Paranaiba",
    "TIETE": "Rio Tiete",
    "PARANA": "Rio Parana / Jupia",
}

DISPLAY_RESERVOIR = {
    "A. VERMELHA": "Agua Vermelha",
    "B. BONITA": "Barra Bonita",
    "C. DOURADA": "Cachoeira Dourada",
    "EMBORCACAO": "Emborcacao",
    "I. SOLTEIRA": "Ilha Solteira",
    "ILHA + T. IRMAOS": "Ilha Solteira + Tres Irmaos",
    "L. C. BARRETO": "Luis Carlos Barreto",
    "N. AVANHANDAVA": "Nova Avanhandava",
    "P. COLOMBIA": "Porto Colombia",
    "PORTO PRIMAVERA": "Porto Primavera",
    "PROMISSAO": "Promissao",
    "SAO SIMAO": "Sao Simao",
    "TRES IRMAOS": "Tres Irmaos",
}


def ascii_key(value: object) -> str:
    text = str(value or "").strip().upper()
    if "TR" in text and "IRM" in text:
        return "TRES IRMAOS"
    if "PROMISS" in text:
        return "PROMISSAO"
    if "EMBORCA" in text:
        return "EMBORCACAO"
    if "SIM" in text and text.startswith("S"):
        return "SAO SIMAO"
    text = text.replace("�", "A")
    text = unicodedata.normalize("NFKD", text)
    text = "".join(ch for ch in text if not unicodedata.combining(ch))
    return text


def load_ons() -> pd.DataFrame:
    files = sorted(RAW_DIR.glob("ons_hidro_*.parquet"))
    if not files:
        raise FileNotFoundError(f"No ONS parquet files found in {RAW_DIR}")
    return pd.concat((pd.read_parquet(path) for path in files), ignore_index=True)


def latest_collection_run() -> Path | None:
    runs = sorted((ROOT / "data" / "runs").glob(COLLECTION_RUN_PATTERN))
    return runs[-1] if runs else None


def load_collection_context() -> dict[str, object]:
    run_dir = latest_collection_run()
    empty = {
        "run_id": "",
        "run_dir": "",
        "summary": {
            "targets_total": 0,
            "collected": 0,
            "errors": 0,
            "station_inventory_rows": 0,
            "requested_station_matches": 0,
            "station_series_collected": 0,
        },
        "requested_station_matches": [],
        "inventory": pd.DataFrame(),
        "series_coverage": pd.DataFrame(),
        "outputs": {},
    }
    if run_dir is None:
        return empty

    manifest_path = run_dir / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8")) if manifest_path.exists() else {}
    inventory_path = run_dir / "collection" / "ana_hidro_soap_inventory" / "station_inventory_matches.csv"
    coverage_path = run_dir / "processing" / "02-station-series-coverage.csv"
    inventory = pd.read_csv(inventory_path) if inventory_path.exists() and inventory_path.stat().st_size else pd.DataFrame()
    series_coverage = pd.read_csv(coverage_path) if coverage_path.exists() and coverage_path.stat().st_size else pd.DataFrame()

    inventory_out = STAGING_DIR / "ana_jupia_station_inventory_matches.csv"
    series_out = STAGING_DIR / "ana_jupia_station_series_coverage.csv"
    if not inventory.empty:
        inventory.to_csv(inventory_out, index=False)
    if not series_coverage.empty:
        series_coverage.to_csv(series_out, index=False)

    collected_series = series_coverage[series_coverage["status"].eq("collected")].copy() if not series_coverage.empty else pd.DataFrame()
    requested = pd.DataFrame(manifest.get("requested_station_matches", []))
    requested_out = ANALYTIC_DIR / "jupia_requested_station_matches.csv"
    series_summary_out = ANALYTIC_DIR / "jupia_station_series_coverage_summary.csv"
    if not requested.empty:
        requested.to_csv(requested_out, index=False)
    if not series_coverage.empty:
        summary = (
            series_coverage.groupby(["status", "series_type"], as_index=False)
            .agg(stations=("station_code", "nunique"), rows=("rows", "sum"))
            .sort_values(["status", "series_type"])
        )
        summary.to_csv(series_summary_out, index=False)

    outputs = {
        "collection_run": str(run_dir),
        "station_inventory": str(inventory_out) if inventory_out.exists() else "",
        "station_series_coverage": str(series_out) if series_out.exists() else "",
        "requested_station_matches": str(requested_out) if requested_out.exists() else "",
        "station_series_summary": str(series_summary_out) if series_summary_out.exists() else "",
    }
    return {
        "run_id": manifest.get("run_id", run_dir.name),
        "run_dir": str(run_dir),
        "summary": manifest.get("summary", empty["summary"]),
        "requested_station_matches": manifest.get("requested_station_matches", []),
        "inventory": inventory,
        "series_coverage": series_coverage,
        "collected_series": collected_series,
        "outputs": outputs,
    }


def build_tables() -> dict[str, object]:
    STAGING_DIR.mkdir(parents=True, exist_ok=True)
    ANALYTIC_DIR.mkdir(parents=True, exist_ok=True)
    collection_context = load_collection_context()

    raw = load_ons()
    raw["basin_key"] = raw["nom_bacia"].map(ascii_key)
    raw["reservoir_key"] = raw["nom_reservatorio"].map(ascii_key)

    mask = raw["basin_key"].isin(TARGET_BASINS)
    for basin, reservoirs in CORE_RESERVOIRS.items():
        mask &= ~((raw["basin_key"] == basin) & ~raw["reservoir_key"].isin(reservoirs))
    df = raw.loc[mask].copy()

    df["date"] = pd.to_datetime(df["din_instante"], errors="coerce")
    df = df[df["date"].notna()].copy()
    df["year"] = df["date"].dt.year
    df["month"] = df["date"].dt.month
    df["year_month"] = df["date"].dt.to_period("M").astype(str)
    df["basin_label"] = df["basin_key"].map(DISPLAY_BASIN)
    df["reservoir_label"] = df["reservoir_key"].map(DISPLAY_RESERVOIR).fillna(
        df["reservoir_key"].str.title()
    )

    numeric_cols = [
        "val_volumeutilcon",
        "val_vazaoafluente",
        "val_vazaodefluente",
        "val_vazaonatural",
        "val_vazaoincremental",
        "val_nivelmontante",
    ]
    for col in numeric_cols:
        df[col] = pd.to_numeric(df[col], errors="coerce")

    staging_cols = [
        "date",
        "year",
        "month",
        "year_month",
        "basin_key",
        "basin_label",
        "reservoir_key",
        "reservoir_label",
        "cod_usina",
        "id_reservatorio",
        *numeric_cols,
    ]
    staging = df[staging_cols].sort_values(["date", "basin_key", "reservoir_key"])
    staging_path = STAGING_DIR / "ons_jupia_contributing_system_daily.csv"
    staging.to_csv(staging_path, index=False)

    monthly = (
        staging.groupby(["basin_key", "basin_label", "reservoir_key", "reservoir_label", "year_month"], as_index=False)
        .agg(
            date=("date", "min"),
            inflow_m3s=("val_vazaoafluente", "mean"),
            outflow_m3s=("val_vazaodefluente", "mean"),
            natural_flow_m3s=("val_vazaonatural", "mean"),
            incremental_flow_m3s=("val_vazaoincremental", "mean"),
            useful_volume_pct=("val_volumeutilcon", "mean"),
            level_upstream_m=("val_nivelmontante", "mean"),
            daily_records=("date", "count"),
        )
        .sort_values(["date", "basin_key", "reservoir_key"])
    )
    monthly_path = ANALYTIC_DIR / "jupia_system_monthly.csv"
    monthly.to_csv(monthly_path, index=False)

    annual = (
        staging.groupby(["basin_key", "basin_label", "reservoir_key", "reservoir_label", "year"], as_index=False)
        .agg(
            inflow_m3s=("val_vazaoafluente", "mean"),
            outflow_m3s=("val_vazaodefluente", "mean"),
            natural_flow_m3s=("val_vazaonatural", "mean"),
            useful_volume_pct=("val_volumeutilcon", "mean"),
            min_useful_volume_pct=("val_volumeutilcon", "min"),
            records=("date", "count"),
        )
    )
    annual_path = ANALYTIC_DIR / "jupia_system_annual.csv"
    annual.to_csv(annual_path, index=False)

    coverage = (
        staging.groupby(["basin_key", "basin_label", "reservoir_key", "reservoir_label"], as_index=False)
        .agg(
            period_start=("date", "min"),
            period_end=("date", "max"),
            records=("date", "count"),
            years=("year", "nunique"),
        )
    )
    coverage["target_years"] = 20
    coverage["coverage_gap_years"] = (coverage["target_years"] - coverage["years"]).clip(lower=0)
    coverage["coverage_status"] = np.where(coverage["years"] >= 20, "meets_target", "below_target")
    coverage_path = ANALYTIC_DIR / "jupia_coverage_matrix.csv"
    coverage.to_csv(coverage_path, index=False)

    basin_summary = (
        monthly.groupby(["basin_key", "basin_label"], as_index=False)
        .agg(
            reservoirs=("reservoir_key", "nunique"),
            mean_inflow_m3s=("inflow_m3s", "mean"),
            mean_outflow_m3s=("outflow_m3s", "mean"),
            mean_volume_pct=("useful_volume_pct", "mean"),
            start=("date", "min"),
            end=("date", "max"),
        )
        .sort_values("mean_inflow_m3s", ascending=False)
    )
    for col in ("start", "end"):
        basin_summary[col] = pd.to_datetime(basin_summary[col]).dt.date.astype(str)
    jupia = monthly[monthly["reservoir_key"] == "JUPIA"].copy()
    jupia_summary = {
        "records_monthly": int(len(jupia)),
        "start": str(jupia["date"].min().date()) if not jupia.empty else "",
        "end": str(jupia["date"].max().date()) if not jupia.empty else "",
        "mean_inflow_m3s": round(float(jupia["inflow_m3s"].mean()), 1) if not jupia.empty else None,
        "mean_outflow_m3s": round(float(jupia["outflow_m3s"].mean()), 1) if not jupia.empty else None,
        "mean_volume_pct": round(float(jupia["useful_volume_pct"].mean()), 1) if not jupia.empty else None,
    }
    collection_summary = collection_context["summary"]
    requested_matches = collection_context["requested_station_matches"]
    collected_series = collection_context.get("collected_series", pd.DataFrame())
    if isinstance(collected_series, pd.DataFrame) and not collected_series.empty:
        series_period_start = str(pd.to_datetime(collected_series["period_start"], errors="coerce").min().date())
        series_period_end = str(pd.to_datetime(collected_series["period_end"], errors="coerce").max().date())
        series_station_count = int(collected_series["station_code"].nunique())
    else:
        series_period_start = ""
        series_period_end = ""
        series_station_count = 0

    context = {
        "report_title": "Bacia Hidrografica de Jupia",
        "report_subtitle": "Sistema contribuinte Paranaiba, Grande, Tiete e no Parana/Jupia",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "scope": {
            "study_slug": "jupia_bacia",
            "primary_node": "UHE Jupia",
            "requested_station": "UHE JUPIA SUCURIU",
            "available_station_note": "A coleta ANA encontrou matches diretos para UHE JUPIA RIO SUCURIU e UHE JUPIA SUCURIU no inventario Hidro; nos dados ONS locais a serie operacional permanece como JUPIA na bacia PARANA.",
            "source": "ONS Dados Hidrologicos de Reservatorios, ANA Hidro/SOAP, ANA GitHub hidro-dados-estacoes-convencionais, IBGE BHB250 e documentos CETESB/ANA.",
            "geographic_scope": "UHE Jupia e entorno Tres Lagoas/Castilho; Rio Sucuriu; Rio Parana; contribuintes Rio Tiete, Rio Grande e Rio Paranaiba no Alto Parana.",
        },
        "metrics": [
            {"label": "Reservatorios ONS", "value": str(int(coverage["reservoir_key"].nunique())), "detail": "Grande, Paranaiba, Tiete e Parana/Jupia", "icon": "water"},
            {"label": "Matches ANA", "value": str(collection_summary.get("requested_station_matches", 0)), "detail": "UHE JUPIA SUCURIU / Rio Sucuriu", "icon": "travel_explore"},
            {"label": "Series ANA", "value": str(collection_summary.get("station_series_collected", 0)), "detail": f"{series_station_count} estacoes com CSV", "icon": "monitoring"},
            {"label": "Janela ONS", "value": f"{staging['year'].min()}-{staging['year'].max()}", "detail": f"{staging['year'].nunique()} anos e {len(staging):,} registros".replace(",", "."), "icon": "calendar_month"},
        ],
        "data_outputs": {
            "staging_daily": str(staging_path),
            "monthly": str(monthly_path),
            "annual": str(annual_path),
            "coverage": str(coverage_path),
            **collection_context["outputs"],
        },
        "collection_summary": collection_summary,
        "collection_run_id": collection_context["run_id"],
        "requested_station_matches": requested_matches,
        "station_series_period": {
            "start": series_period_start,
            "end": series_period_end,
            "stations": series_station_count,
        },
        "basin_summary": basin_summary.to_dict(orient="records"),
        "jupia_summary": jupia_summary,
        "known_gaps": [
            "A serie operacional ONS local continua identificada como JUPIA, nao como SUCURIU; a identidade SUCURIU foi confirmada no inventario ANA/Hidro.",
            "O codigo ANA 63003300 (UHE JUPIA SUCURIU) foi encontrado no inventario, mas nao possui CSV historico no branch dev do repositorio ANA baixado nesta rodada.",
            "Foram preservados PDFs/HTML de qualidade da agua e poluicao; a extracao parametrica desses documentos ainda deve virar uma camada propria para correlacao.",
            "Dados do Tiete ja usados no relatorio anterior entram aqui como uma subcamada contribuinte, nao como narrativa principal.",
        ],
        "figures": [
            {
                "id": "fig1",
                "file": "fig1_basin_system_overview.svg",
                "title": "Sistema contribuinte de Jupia",
                "tag": "Estrutura",
                "tag_color": "blue",
                "icon": "account_tree",
                "summary": "Diagrama dos quatro blocos operacionais usados nesta primeira leitura: Grande, Paranaiba, Tiete e Parana/Jupia.",
                "interpretation": "Jupia deve ser lido como no integrador do Alto Parana. O Tiete continua relevante, mas agora aparece junto com Grande, Paranaiba e o eixo Sucuriu/Jupia confirmado no inventario ANA.",
                "highlight": "A unidade analitica deixa de ser apenas a cascata do Tiete e passa a ser a bacia contribuinte integrada de Jupia.",
            },
            {
                "id": "fig2",
                "file": "fig2_monthly_inflow_by_basin.svg",
                "title": "Vazao afluente mensal por grande contribuinte",
                "tag": "Hidrologia",
                "tag_color": "green",
                "icon": "waves",
                "summary": "Serie mensal media de vazao afluente por bacia operacional ONS, agregando os reservatorios selecionados em cada contribuinte.",
                "interpretation": "A comparacao mostra a escala relativa dos contribuintes que condicionam Jupia. Grande e Paranaiba ampliam fortemente o contexto hidrologico em relacao a uma leitura Tiete-only.",
                "highlight": "O relatorio de Jupia precisa reunir os tres grandes rios em vez de reaproveitar apenas a narrativa do Tiete.",
            },
            {
                "id": "fig3",
                "file": "fig3_jupia_node_series.svg",
                "title": "No Jupia: afluencia, defluencia e volume util",
                "tag": "Jupia",
                "tag_color": "orange",
                "icon": "water_drop",
                "summary": "Serie mensal da UHE Jupia no ONS, com vazoes afluente/defluente e volume util medio.",
                "interpretation": "A serie posiciona Jupia como receptor operacional do sistema. A coleta complementar ja identificou os codigos ANA ligados a UHE Jupia/Sucuriu, permitindo uma ponte posterior com series convencionais e qualidade da agua.",
                "highlight": "Nos dados ONS, o ponto auditavel e JUPIA; no inventario ANA, UHE JUPIA SUCURIU aparece com codigo 63003300.",
            },
            {
                "id": "fig4",
                "file": "fig4_annual_min_volume_heatmap.svg",
                "title": "Anos criticos por reservatorio",
                "tag": "Estresse hidrico",
                "tag_color": "red",
                "icon": "grid_view",
                "summary": "Mapa de calor do volume util minimo anual para os reservatorios selecionados.",
                "interpretation": "O painel permite identificar anos de estresse sincronizado e diferenciar respostas de cabeceira, contribuintes e no receptor.",
                "highlight": "Eventos secos devem ser avaliados como sinais sistêmicos, nao como anomalias isoladas de uma unica cascata.",
            },
            {
                "id": "fig5",
                "file": "fig5_reservoir_count_and_flow.svg",
                "title": "Cobertura de estacoes e escala hidrologica",
                "tag": "Cobertura",
                "tag_color": "purple",
                "icon": "bar_chart",
                "summary": "Comparacao entre numero de reservatorios ONS selecionados e vazao media por bacia contribuinte.",
                "interpretation": "O grafico explicita por que a demanda pede Jupia: a bacia ampliada agrega mais pontos operacionais e maior diversidade hidrologica do que a leitura Tiete isolada.",
                "highlight": "Paranaiba e Grande acrescentam densidade operacional e contexto hidrologico ao no Jupia.",
            },
            {
                "id": "fig6",
                "file": "fig6_coverage_matrix.svg",
                "title": "Cobertura temporal da base usada",
                "tag": "Auditoria",
                "tag_color": "stone",
                "icon": "fact_check",
                "summary": "Matriz de cobertura temporal por bacia e reservatorio, comparada ao alvo minimo de 20 anos.",
                "interpretation": "A base ONS local atende ao alvo temporal para os principais reservatorios selecionados. A coleta operacional acrescenta inventario ANA e documentos brutos para qualidade/poluicao, mas a serie exata 63003300 ainda nao veio como CSV historico.",
                "highlight": "A camada Jupia agora tem descoberta, inventario de estacoes e coleta bruta rastreavel; falta extrair os documentos de qualidade/poluicao para variaveis tabulares.",
            },
            {
                "id": "fig7",
                "file": "fig7_station_collection_evidence.svg",
                "title": "Evidencia de coleta: estacoes Jupia/Sucuriu",
                "tag": "Coleta",
                "tag_color": "blue",
                "icon": "dataset",
                "summary": "Resumo dos matches ANA/Hidro para UHE Jupia/Sucuriu e das series historicas convencionais disponiveis no repositorio ANA/GitHub.",
                "interpretation": "A demanda UHE JUPIA SUCURIU foi localizada no inventario oficial, mas a disponibilidade de CSV historico varia por codigo. Isso separa identidade da estacao, disponibilidade de serie e lacuna operacional.",
                "highlight": f"Foram encontrados {collection_summary.get('requested_station_matches', 0)} matches diretos para a estacao solicitada e {collection_summary.get('station_series_collected', 0)} series CSV convencionais em codigos proximos.",
            },
        ],
    }
    CONTEXT_PATH.write_text(json.dumps(context, ensure_ascii=False, indent=2), encoding="utf-8")

    return {
        "staging_rows": len(staging),
        "monthly_rows": len(monthly),
        "annual_rows": len(annual),
        "coverage_rows": len(coverage),
        "context_path": str(CONTEXT_PATH),
    }


def main() -> None:
    result = build_tables()
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
