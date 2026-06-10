"""Prepare staging and analytic tables for the Jupia contributing basin report."""

from __future__ import annotations

import json
import re
import unicodedata
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

re_daily = re.compile(r"^(Vazao|Cota)\d{2}$")


ROOT = Path(__file__).resolve().parents[2]
RAW_DIR = ROOT / "data" / "raw" / "operacao_reservatorio"
STAGING_DIR = ROOT / "data" / "staging" / "jupia_bacia"
ANALYTIC_DIR = ROOT / "data" / "analytic" / "jupia_bacia"
CONTEXT_PATH = Path(__file__).resolve().parent / "report_context.json"
COLLECTION_RUN_PATTERN = "operational-collect-jupia-*"
SUPPLEMENT_RUN_PATTERN = "operational-supplement-jupia-*"
INFOAGUAS_RUN_PATTERN = "operational-infoaguas-jupia-*"
OPENALEX_RUN_PATTERN = "perplexity-intel-*"
QUEIMADAS_PARQUET = ROOT / "data" / "staging" / "queimadas" / "focos_calor_evento.parquet"

# Contorno esquematico da bacia contribuinte ate Jupia (lat, lon), acompanhando os
# divisores aproximados: Sucuriu/Verde (W), Paranaiba ate o DF (N), Sao Francisco (NE),
# Grande na Mantiqueira (E), Tiete (SE) e Paranapanema (S), fechando no outlet.
# Fonte unica para fig0, mapa interativo e filtros espaciais.
BASIN_OUTLINE = [
    (-20.87, -51.63), (-19.8, -52.9), (-18.6, -53.2), (-17.6, -52.4), (-16.8, -50.8),
    (-15.9, -49.3), (-15.6, -47.9), (-16.5, -46.9), (-17.8, -46.3), (-19.0, -45.8),
    (-20.2, -44.9), (-21.5, -44.6), (-22.4, -44.9), (-22.8, -45.5), (-23.4, -46.0),
    (-23.6, -47.5), (-23.2, -49.0), (-22.7, -50.3), (-22.0, -51.3), (-20.87, -51.63),
]


def in_basin_mask(latitudes: pd.Series, longitudes: pd.Series) -> pd.Series:
    """Vectorized point-in-polygon test against the schematic basin outline."""
    from matplotlib.path import Path as MplPath

    polygon = MplPath([(lon, lat) for lat, lon in BASIN_OUTLINE])
    points = np.column_stack([longitudes.to_numpy(dtype=float), latitudes.to_numpy(dtype=float)])
    return pd.Series(polygon.contains_points(points), index=latitudes.index)

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

TRACK_THEME = {
    "n1_jupia_sucuriu_station_known_sources": "Jupia/Sucuriu",
    "n1_geografia_bacia_jupia_ottobacias": "Comportamento da bacia",
    "n2_operacao_reservatorios_ons_sar": "Comportamento dos rios",
    "n2_hidrologia_ana_hidroweb_parana_grande_paranaiba_tiete_sucuriu": "Comportamento dos rios",
    "n3_qualidade_agua_cetesb_ana_infoaguas": "Poluicao e qualidade da agua",
    "n3_poluicao_saneamento_efluentes_outorgas": "Poluicao e qualidade da agua",
    "n3_sedimentos_turbidez_assoreamento_jupia": "Sedimentos e turbidez",
    "n2_uso_solo_agro_queimadas_mapbiomas_inpe_ibge": "Pressao territorial",
    "n2_clima_chuva_seca_jupia": "Clima e variabilidade",
    "n4_literatura_contexto_integrado_jupia": "Correlacao integrada",
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


def latest_openalex_run() -> Path | None:
    candidates = [
        path
        for path in (ROOT / "data" / "runs").glob(OPENALEX_RUN_PATTERN)
        if (path / "collection" / "raw-openalex-works.json").exists()
    ]
    if not candidates:
        return None
    return max(candidates, key=lambda path: (path / "collection" / "raw-openalex-works.json").stat().st_mtime)


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


def load_openalex_context(collection_context: dict[str, object]) -> dict[str, object]:
    run_dir = latest_openalex_run()
    empty = {
        "run_id": "",
        "run_dir": "",
        "summary": {
            "raw_works": 0,
            "works": 0,
            "open_access": 0,
            "with_pdf": 0,
            "theme_count": 0,
            "period_start": "",
            "period_end": "",
        },
        "top_works": [],
        "outputs": {},
    }
    if run_dir is None:
        return empty

    raw_path = run_dir / "collection" / "raw-openalex-works.json"
    manifest_path = run_dir / "manifest.json"
    raw_works = json.loads(raw_path.read_text(encoding="utf-8"))
    manifest = json.loads(manifest_path.read_text(encoding="utf-8")) if manifest_path.exists() else {}

    rows = []
    for work in raw_works:
        track = str(work.get("query_id", ""))
        search_text = str(work.get("search_text", ""))
        # Map query ids back to track names from the saved search plan.
        search_plan_path = run_dir / "search-plan.json"
        search_plan = json.loads(search_plan_path.read_text(encoding="utf-8")) if search_plan_path.exists() else []
        track_by_query = {item["query_id"]: item.get("research_track", "") for item in search_plan}
        track_name = track_by_query.get(track, track)
        rows.append(
            {
                "openalex_id": work.get("openalex_id", ""),
                "doi": work.get("doi", ""),
                "title": work.get("title", ""),
                "publication_year": work.get("publication_year"),
                "publication_date": work.get("publication_date", ""),
                "work_type": work.get("work_type", ""),
                "cited_by_count": work.get("cited_by_count", 0),
                "is_open_access": bool(work.get("is_open_access")),
                "has_pdf": bool(work.get("pdf_url")),
                "pdf_url": work.get("pdf_url", ""),
                "oa_url": work.get("oa_url", ""),
                "landing_page_url": work.get("landing_page_url", ""),
                "source_display_name": work.get("source_display_name", ""),
                "authors": "|".join(work.get("authors", [])),
                "institutions": "|".join(work.get("institutions", [])),
                "countries": "|".join(work.get("countries", [])),
                "keywords": "|".join(work.get("keywords", [])),
                "concepts": "|".join(work.get("concepts", [])),
                "abstract": work.get("abstract", ""),
                "search_text": search_text,
                "research_track": track_name,
                "theme": TRACK_THEME.get(track_name, "Literatura academica"),
                "source_url": work.get("pdf_url") or work.get("oa_url") or work.get("doi") or work.get("landing_page_url") or work.get("openalex_url", ""),
            }
        )

    works = pd.DataFrame(rows)
    if works.empty:
        return empty
    works = works.sort_values(["cited_by_count", "publication_year"], ascending=[False, False])
    works = works.drop_duplicates(subset=["openalex_id"]).copy()
    works["publication_year"] = pd.to_numeric(works["publication_year"], errors="coerce")

    staging_path = STAGING_DIR / "openalex_jupia_works.csv"
    works.to_csv(staging_path, index=False)

    theme_summary = (
        works.groupby("theme", as_index=False)
        .agg(
            works=("openalex_id", "count"),
            open_access=("is_open_access", "sum"),
            with_pdf=("has_pdf", "sum"),
            first_year=("publication_year", "min"),
            last_year=("publication_year", "max"),
            citations=("cited_by_count", "sum"),
        )
        .sort_values(["works", "citations"], ascending=False)
    )
    theme_path = ANALYTIC_DIR / "jupia_openalex_theme_summary.csv"
    theme_summary.to_csv(theme_path, index=False)

    evidence = works[
        [
            "theme",
            "title",
            "publication_year",
            "cited_by_count",
            "source_display_name",
            "source_url",
            "doi",
            "has_pdf",
            "is_open_access",
            "research_track",
        ]
    ].copy()
    evidence_path = ANALYTIC_DIR / "jupia_academic_evidence.csv"
    evidence.to_csv(evidence_path, index=False)

    locations = build_evidence_locations(collection_context)
    locations_path = ANALYTIC_DIR / "jupia_evidence_locations.csv"
    locations.to_csv(locations_path, index=False)

    years = works["publication_year"].dropna()
    summary = {
        "raw_works": int(len(raw_works)),
        "works": int(len(works)),
        "open_access": int(works["is_open_access"].sum()),
        "with_pdf": int(works["has_pdf"].sum()),
        "theme_count": int(works["theme"].nunique()),
        "period_start": str(int(years.min())) if not years.empty else "",
        "period_end": str(int(years.max())) if not years.empty else "",
    }
    outputs = {
        "openalex_run": str(run_dir),
        "openalex_works": str(staging_path),
        "academic_evidence": str(evidence_path),
        "openalex_theme_summary": str(theme_path),
        "evidence_locations": str(locations_path),
    }
    return {
        "run_id": manifest.get("research_id", run_dir.name),
        "run_dir": str(run_dir),
        "summary": summary,
        "top_works": evidence.head(10).to_dict(orient="records"),
        "outputs": outputs,
    }


def build_evidence_locations(collection_context: dict[str, object]) -> pd.DataFrame:
    rows = [
        {
            "name": "UHE Jupia / Rio Parana",
            "kind": "no receptor",
            "longitude": -51.63,
            "latitude": -20.78,
            "source_layer": "ONS operacao + literatura OpenAlex",
            "notes": "No integrador usado para correlacionar sinais hidrologicos e pressoes.",
        },
        {
            "name": "Corredor Rio Tiete",
            "kind": "area contribuinte",
            "longitude": -49.2,
            "latitude": -21.9,
            "source_layer": "ONS + CETESB/InfoAguas + literatura",
            "notes": "Sub-bacia poluente e operacional que chega ao Alto Parana.",
        },
        {
            "name": "Rio Grande",
            "kind": "area contribuinte",
            "longitude": -48.3,
            "latitude": -20.0,
            "source_layer": "ONS + literatura",
            "notes": "Grande contribuinte hidrologico a montante de Jupia.",
        },
        {
            "name": "Rio Paranaiba",
            "kind": "area contribuinte",
            "longitude": -48.8,
            "latitude": -18.6,
            "source_layer": "ONS + literatura",
            "notes": "Grande contribuinte hidrologico a montante de Jupia.",
        },
        {
            "name": "Alto Parana / La Plata",
            "kind": "area academica",
            "longitude": -55.0,
            "latitude": -24.0,
            "source_layer": "OpenAlex",
            "notes": "Area ampla de estudos hidrologicos/climaticos usados como contexto regional.",
        },
    ]
    requested = collection_context.get("requested_station_matches", [])
    if isinstance(requested, list):
        for item in requested:
            try:
                lat = float(str(item.get("Latitude", "")).replace(",", "."))
                lon = float(str(item.get("Longitude", "")).replace(",", "."))
            except (TypeError, ValueError):
                continue
            rows.append(
                {
                    "name": str(item.get("Nome", "Estacao ANA")),
                    "kind": "estacao ANA/Hidro",
                    "longitude": lon,
                    "latitude": lat,
                    "source_layer": "ANA Hidro/SOAP",
                    "notes": f"Codigo {item.get('Codigo', '')}; rio {item.get('RioNome', '') or 'nao informado'}",
                }
            )
    return pd.DataFrame(rows)


def fix_mojibake(value: str) -> str:
    try:
        return value.encode("latin-1").decode("utf-8")
    except (UnicodeEncodeError, UnicodeDecodeError):
        return value


def load_soap_series(supplement_run: Path | None) -> list[pd.DataFrame]:
    """Monthly series collected via SOAP HidroSerieHistorica in the supplemental run."""
    if supplement_run is None:
        return []
    folder = supplement_run / "collection" / "ana_hidro_soap_series"
    frames: list[pd.DataFrame] = []
    for path in sorted(folder.glob("*.csv")):
        try:
            serie = pd.read_csv(path, dtype=str)
        except (pd.errors.EmptyDataError, ValueError):
            continue
        if serie.empty or "DataHora" not in serie.columns:
            continue
        code_str, _, label = path.stem.partition("_")
        dates = pd.to_datetime(serie["DataHora"], errors="coerce")
        # O SOAP costuma devolver "Media" vazio; usa a media das colunas diarias
        # (Vazao01..31 / Cota01..31) como fallback.
        monthly_mean = pd.to_numeric(serie.get("Media"), errors="coerce")
        daily_cols = [c for c in serie.columns if re_daily.match(c)]
        if daily_cols:
            daily_mean = serie[daily_cols].apply(pd.to_numeric, errors="coerce").mean(axis=1)
            monthly_mean = monthly_mean.fillna(daily_mean)
        tidy = pd.DataFrame(
            {
                "station_code": int(code_str),
                "station_name": "",
                "river_name": "",
                "series_type": label or "vazoes",
                "consistency_level": pd.to_numeric(serie.get("NivelConsistencia"), errors="coerce"),
                "date": dates.dt.to_period("M").dt.to_timestamp(),
                "monthly_mean": monthly_mean,
            }
        )
        tidy = tidy[tidy["date"].notna() & tidy["monthly_mean"].notna()]
        if not tidy.empty:
            frames.append(tidy)
    return frames


def build_station_monthly_series(
    collection_context: dict[str, object], supplement_run: Path | None = None
) -> tuple[str, dict[str, object]]:
    """Tidy monthly series (vazoes/cotas) from the ANA CSVs collected in the run."""
    coverage = collection_context.get("series_coverage", pd.DataFrame())
    inventory = collection_context.get("inventory", pd.DataFrame())
    if not isinstance(coverage, pd.DataFrame) or coverage.empty:
        return "", {}

    names: dict[int, dict[str, str]] = {}
    if isinstance(inventory, pd.DataFrame) and not inventory.empty:
        for _, row in inventory.drop_duplicates("Codigo").iterrows():
            names[int(row["Codigo"])] = {
                "station_name": str(row.get("Nome", "") or ""),
                "river_name": str(row.get("RioNome", "") or ""),
                "municipality": str(row.get("nmMunicipio", "") or ""),
                "state": str(row.get("nmEstado", "") or ""),
            }

    collected = coverage[(coverage["status"] == "collected") & (pd.to_numeric(coverage["rows"], errors="coerce") > 0)]
    frames = []
    for _, row in collected.iterrows():
        src = Path(str(row["source_path"]))
        if not src.exists():
            continue
        serie = pd.read_csv(src, sep=";", dtype=str)
        if serie.empty or "Media" not in serie.columns or "Data" not in serie.columns:
            continue
        code = int(row["station_code"])
        meta = names.get(code, {})
        tidy = pd.DataFrame(
            {
                "station_code": code,
                "station_name": meta.get("station_name", ""),
                "river_name": meta.get("river_name", ""),
                "series_type": str(row["series_type"]),
                "consistency_level": pd.to_numeric(serie.get("NivelConsistencia"), errors="coerce"),
                "date": pd.to_datetime(serie["Data"], format="%m/%Y", errors="coerce"),
                "monthly_mean": pd.to_numeric(serie["Media"], errors="coerce"),
            }
        )
        tidy = tidy[tidy["date"].notna() & tidy["monthly_mean"].notna()]
        frames.append(tidy)
    frames.extend(load_soap_series(supplement_run))
    if not frames:
        return "", {}

    series = pd.concat(frames, ignore_index=True)
    # Completa nome/rio das series SOAP a partir do inventario.
    if names:
        meta = pd.DataFrame.from_dict(names, orient="index").rename_axis("station_code").reset_index()
        series = series.merge(meta[["station_code", "station_name", "river_name"]], on="station_code", how="left", suffixes=("", "_inv"))
        series["station_name"] = series["station_name"].mask(series["station_name"].eq(""), series["station_name_inv"])
        series["river_name"] = series["river_name"].mask(series["river_name"].eq(""), series["river_name_inv"])
        series = series.drop(columns=["station_name_inv", "river_name_inv"])
    # Quando ha nivel bruto e consistido para o mesmo mes, mantem o consistido.
    series = (
        series.sort_values(["station_code", "series_type", "date", "consistency_level"])
        .drop_duplicates(["station_code", "series_type", "date"], keep="last")
        .drop(columns=["consistency_level"])
    )
    out = STAGING_DIR / "ana_jupia_station_monthly_series.csv"
    series.to_csv(out, index=False)
    summary = {
        "stations": int(series["station_code"].nunique()),
        "rows": int(len(series)),
        "start": str(series["date"].min().date()),
        "end": str(series["date"].max().date()),
    }
    return str(out), summary


def latest_supplement_run() -> Path | None:
    runs = sorted((ROOT / "data" / "runs").glob(SUPPLEMENT_RUN_PATTERN))
    return runs[-1] if runs else None


def build_quality_tables(supplement_run: Path | None) -> tuple[dict[str, str], dict[str, object]]:
    """Tidy annual water-quality series from the ANA ArcGIS indicator layers."""
    if supplement_run is None:
        return {}, {}
    folder = supplement_run / "collection" / "ana_arcgis_quality_indicators"
    files = sorted(folder.glob("quality_*_annual_series.json"))
    if not files:
        return {}, {}

    records: list[dict[str, object]] = []
    for path in files:
        payload = json.loads(path.read_text(encoding="utf-8"))
        parameter = payload.get("parameter", path.stem)
        label = payload.get("label", parameter)
        for feature in payload.get("features", []):
            attrs = feature.get("attributes", {})
            base = {
                "parameter": parameter,
                "parameter_label": label,
                "station_code": str(attrs.get("CDESTACAO", "") or ""),
                "entity": str(attrs.get("ENTIDADE", "") or ""),
                "water_body": str(attrs.get("CORPODAGUA", "") or ""),
                "uf": str(attrs.get("SGUF", "") or ""),
                "latitude": attrs.get("LATITUDE"),
                "longitude": attrs.get("LONGITUDE"),
            }
            for key, value in attrs.items():
                if value is None or not isinstance(key, str):
                    continue
                for prefix, column in (("MED_", "mean"), ("MIN_", "min"), ("MAX_", "max")):
                    if key.startswith(prefix):
                        year = key[len(prefix):]
                        if year.isdigit():
                            records.append({**base, "year": int(year), "stat": column, "value": value})

    if not records:
        return {}, {}
    quality = pd.DataFrame(records)
    quality["value"] = pd.to_numeric(quality["value"], errors="coerce")
    quality = quality[quality["value"].notna()]
    quality = quality.pivot_table(
        index=["parameter", "parameter_label", "station_code", "entity", "water_body", "uf", "latitude", "longitude", "year"],
        columns="stat",
        values="value",
        aggfunc="mean",
    ).reset_index()
    quality.columns.name = None
    quality["latitude"] = pd.to_numeric(quality["latitude"], errors="coerce")
    quality["longitude"] = pd.to_numeric(quality["longitude"], errors="coerce")
    quality = quality[quality["latitude"].notna() & quality["longitude"].notna()]
    quality["in_basin"] = in_basin_mask(quality["latitude"], quality["longitude"])

    staging_path = STAGING_DIR / "ana_quality_indicators_annual.csv"
    quality.sort_values(["parameter", "station_code", "year"]).to_csv(staging_path, index=False)

    basin = quality[quality["in_basin"]].copy()
    analytic_path = ANALYTIC_DIR / "jupia_quality_annual.csv"
    basin.sort_values(["parameter", "station_code", "year"]).to_csv(analytic_path, index=False)

    stations_path = ANALYTIC_DIR / "jupia_quality_stations.csv"
    stations = (
        basin.groupby(["station_code", "entity", "water_body", "uf", "latitude", "longitude"], as_index=False)
        .agg(parameters=("parameter", "nunique"), first_year=("year", "min"), last_year=("year", "max"), years=("year", "nunique"))
        .sort_values(["uf", "station_code"])
    )
    stations.to_csv(stations_path, index=False)

    summary = {
        "stations_bbox": int(quality["station_code"].nunique()),
        "stations_in_basin": int(basin["station_code"].nunique()),
        "stations_ms": int(basin.loc[basin["uf"] == "MS", "station_code"].nunique()),
        "parameters": sorted(basin["parameter"].unique().tolist()),
        "period": f"{int(basin['year'].min())}-{int(basin['year'].max())}" if not basin.empty else "",
        "rows_in_basin": int(len(basin)),
    }
    outputs = {
        "quality_staging": str(staging_path),
        "quality_annual": str(analytic_path),
        "quality_stations": str(stations_path),
        "supplement_run": str(supplement_run),
    }
    return outputs, summary


def latest_infoaguas_run() -> Path | None:
    runs = [
        path
        for path in (ROOT / "data" / "runs").glob(INFOAGUAS_RUN_PATTERN)
        if (path / "processing" / "infoaguas_samples.csv").exists()
    ]
    return max(runs, key=lambda p: p.name) if runs else None


def dms_to_decimal(value: str) -> float | None:
    """Converte '21 02 54' (DMS, hemisferio sul/oeste) para decimal negativo."""
    parts = re.findall(r"[\d.]+", str(value or ""))
    if not parts:
        return None
    degrees = float(parts[0])
    minutes = float(parts[1]) if len(parts) > 1 else 0.0
    seconds = float(parts[2]) if len(parts) > 2 else 0.0
    return -(degrees + minutes / 60 + seconds / 3600)


def build_infoaguas_tables(infoaguas_run: Path | None) -> tuple[dict[str, str], dict[str, object]]:
    """Tidy CETESB InfoAguas samples (per-collection measurements) into staging/analytic."""
    if infoaguas_run is None:
        return {}, {}
    samples = pd.read_csv(infoaguas_run / "processing" / "infoaguas_samples.csv", dtype=str)
    if samples.empty:
        return {}, {}

    tidy = pd.DataFrame(
        {
            "point_code": samples["Código Ponto"],
            "date": pd.to_datetime(samples["Data Coleta"], dayfirst=True, errors="coerce"),
            "parameter": samples["Parametro"].str.strip(),
            "sign": samples.get("Sinal", "").fillna(""),
            "value": pd.to_numeric(samples["Valor"].str.replace(",", ".", regex=False), errors="coerce"),
            "unit": samples.get("Unidade", "").fillna(""),
            "hydric_system": samples.get("Sistema Hídrico", "").fillna(""),
            "conama_class": samples.get("CLASSE", "").fillna(""),
            "municipality": samples.get("Município", "").fillna(""),
            "ugrhi": samples.get("UGRHI", "").fillna(""),
            "latitude": samples.get("Latitude", "").map(dms_to_decimal),
            "longitude": samples.get("Longitude", "").map(dms_to_decimal),
        }
    )
    tidy = tidy[tidy["date"].notna() & tidy["value"].notna() & tidy["parameter"].astype(bool)]
    tidy = tidy.drop_duplicates(["point_code", "date", "parameter", "value"])
    staging_path = STAGING_DIR / "cetesb_infoaguas_samples.csv"
    tidy.sort_values(["point_code", "parameter", "date"]).to_csv(staging_path, index=False)

    monthly = tidy.copy()
    monthly["year_month"] = monthly["date"].dt.to_period("M").dt.to_timestamp()
    monthly = (
        monthly.groupby(["point_code", "hydric_system", "parameter", "unit", "year_month"], as_index=False)
        .agg(value=("value", "mean"), samples=("value", "size"))
    )
    analytic_path = ANALYTIC_DIR / "jupia_infoaguas_monthly.csv"
    monthly.to_csv(analytic_path, index=False)

    summary = {
        "points": sorted(tidy["point_code"].unique().tolist()),
        "parameters": int(tidy["parameter"].nunique()),
        "samples": int(len(tidy)),
        "period": f"{tidy['date'].min().date()} a {tidy['date'].max().date()}",
        "run_id": infoaguas_run.name,
    }
    outputs = {
        "infoaguas_staging": str(staging_path),
        "infoaguas_monthly": str(analytic_path),
        "infoaguas_run": str(infoaguas_run),
    }
    return outputs, summary


def build_queimadas_summary(supplement_run: Path | None) -> tuple[str, dict[str, object]]:
    """Annual hot-spot counts. Prefers the basin-wide supplemental WFS collection;
    falls back to the Tiete-corridor parquet staged for the previous study."""
    frames: list[pd.DataFrame] = []
    source = ""
    if supplement_run is not None:
        folder = supplement_run / "collection" / "queimadas_bacia"
        for path in sorted(folder.glob("focos_*_todosats.csv")):
            try:
                df = pd.read_csv(path, usecols=lambda c: c in {"latitude", "longitude", "data_hora_gmt", "estado", "municipio", "bioma"})
            except (ValueError, pd.errors.EmptyDataError):
                continue
            if df.empty:
                continue
            df["ano"] = pd.to_datetime(df["data_hora_gmt"], errors="coerce").dt.year
            frames.append(df.drop(columns=["data_hora_gmt"]))
        source = "wfs_bacia"

    if frames:
        focos = pd.concat(frames, ignore_index=True)
        focos = focos[focos["ano"].notna()].copy()
        focos["ano"] = focos["ano"].astype(int)
        focos["estado"] = focos["estado"].astype(str).map(fix_mojibake).str.upper()
        focos["in_basin"] = in_basin_mask(focos["latitude"], focos["longitude"])
        staging_path = STAGING_DIR / "queimadas_bacia_focos.parquet"
        focos.to_parquet(staging_path, index=False)
        basin = focos[focos["in_basin"]]
        summary = (
            basin.groupby(["estado", "ano"], as_index=False)
            .size()
            .rename(columns={"size": "focos"})
            .sort_values(["estado", "ano"])
        )
    elif QUEIMADAS_PARQUET.exists():
        focos = pd.read_parquet(QUEIMADAS_PARQUET, columns=["ano", "estado"])
        focos["estado"] = focos["estado"].astype(str).map(fix_mojibake)
        basin = focos
        summary = (
            focos.groupby(["estado", "ano"], as_index=False)
            .size()
            .rename(columns={"size": "focos"})
            .sort_values(["estado", "ano"])
        )
        source = "parquet_corredor_tiete"
    else:
        return "", {}

    out = ANALYTIC_DIR / "jupia_queimadas_bacia_estado_ano.csv"
    summary.to_csv(out, index=False)
    stats = {
        "total_focos": int(len(basin)),
        "period": f"{int(basin['ano'].min())}-{int(basin['ano'].max())}",
        "states": sorted(summary["estado"].unique().tolist()),
        "source": source,
    }
    return str(out), stats


def build_tables() -> dict[str, object]:
    STAGING_DIR.mkdir(parents=True, exist_ok=True)
    ANALYTIC_DIR.mkdir(parents=True, exist_ok=True)
    collection_context = load_collection_context()
    openalex_context = load_openalex_context(collection_context)
    supplement_run = latest_supplement_run()
    station_series_path, station_series_summary = build_station_monthly_series(collection_context, supplement_run)
    queimadas_path, queimadas_summary = build_queimadas_summary(supplement_run)
    quality_outputs, quality_summary = build_quality_tables(supplement_run)
    infoaguas_outputs, infoaguas_summary = build_infoaguas_tables(latest_infoaguas_run())

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
            "academic_source": "OpenAlex API /works, rodada academica Jupia sem Perplexity, com raw JSON preservado.",
            "geographic_scope": "UHE Jupia e entorno Tres Lagoas/Castilho; Rio Sucuriu; Rio Parana; contribuintes Rio Tiete, Rio Grande e Rio Paranaiba no Alto Parana.",
        },
        "spatial_recorte": {
            "title": "Recorte geografico analisado",
            "short_name": "Bacia contribuinte do Alto Parana ate a UHE Jupia",
            "outlet": "Outlet analitico no Rio Parana, proximo a UHE Jupia / Eng. Souza Dias, entre Tres Lagoas-MS e Castilho/Andradina-SP.",
            "outlet_coordinates": "-20.868, -51.628",
            "watershed_area_note": "Area delineada no site de bacias globais: aproximadamente 480.000 km2 a montante do outlet.",
            "definition": "Este relatorio analisa a area que drena para Jupia antes do ponto de saida no Rio Parana. O recorte nao e a bacia do Tiete isolada e tambem nao e apenas o reservatorio de Jupia; e o sistema contribuinte do Alto Parana que combina Paranaiba, Grande, Tiete e Parana no no receptor de Jupia.",
            "main_basin": "Alto Parana / Parana superior ate Jupia",
            "structuring_rivers": ["Rio Paranaiba", "Rio Grande", "Rio Tiete", "Rio Parana"],
            "local_focus": ["UHE Jupia / Eng. Souza Dias", "Rio Sucuriu", "estacoes ANA/Hidro UHE JUPIA SUCURIU", "entorno Tres Lagoas-Castilho-Andradina"],
            "analysis_question": "Como os rios Paranaiba, Grande, Tiete e Parana, junto com operacao de reservatorios, poluicao, uso do solo, clima e sedimentos, condicionam o no receptor de Jupia?",
        },
        "metrics": [
            {"label": "Reservatorios ONS", "value": str(int(coverage["reservoir_key"].nunique())), "detail": "Grande, Paranaiba, Tiete e Parana/Jupia", "icon": "water"},
            {"label": "Matches ANA", "value": str(collection_summary.get("requested_station_matches", 0)), "detail": "UHE JUPIA SUCURIU / Rio Sucuriu", "icon": "travel_explore"},
            {"label": "Series ANA", "value": str(collection_summary.get("station_series_collected", 0)), "detail": f"{series_station_count} estacoes com CSV", "icon": "monitoring"},
            {"label": "Janela ONS", "value": f"{staging['year'].min()}-{staging['year'].max()}", "detail": f"{staging['year'].nunique()} anos e {len(staging):,} registros".replace(",", "."), "icon": "calendar_month"},
            {"label": "Qualidade ANA", "value": str(quality_summary.get("stations_in_basin", 0)), "detail": f"estacoes na bacia · {quality_summary.get('period', 'sem serie')}", "icon": "science"},
            {"label": "OpenAlex", "value": str(openalex_context["summary"].get("works", 0)), "detail": f"{openalex_context['summary'].get('with_pdf', 0)} com PDF/arquivo", "icon": "article"},
        ],
        "data_outputs": {
            "staging_daily": str(staging_path),
            "monthly": str(monthly_path),
            "annual": str(annual_path),
            "coverage": str(coverage_path),
            "station_monthly_series": station_series_path,
            "queimadas_estado_ano": queimadas_path,
            **quality_outputs,
            **infoaguas_outputs,
            **collection_context["outputs"],
            **openalex_context["outputs"],
        },
        "station_series_summary_stats": station_series_summary,
        "queimadas_summary": queimadas_summary,
        "quality_summary": quality_summary,
        "infoaguas_summary": infoaguas_summary,
        "collection_summary": collection_summary,
        "collection_run_id": collection_context["run_id"],
        "openalex_run_id": openalex_context["run_id"],
        "openalex_summary": openalex_context["summary"],
        "top_academic_sources": openalex_context["top_works"],
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
            "O codigo ANA 63003300 (UHE JUPIA SUCURIU) segue sem serie aberta: nao ha CSV no repositorio ANA/GitHub, o SOAP HidroSerieHistorica retorna vazio e o download Hidroweb agora exige autenticacao (HTTP 401).",
            "A qualidade da agua tem duas camadas tabulares: indicadores anuais ANA/RNQA (ate 2021) e amostras por coleta do CETESB InfoAguas (ate 2026). A coleta InfoAguas e parcial: cobre 7 pontos da UGRHI 19 (Baixo Tiete); faltam os demais pontos da UGRHI 19 e as UGRHIs 18, 15 e 12 e o eixo Rio Parana, interrompidos a pedido.",
            "A OpenAlex melhorou a cobertura academica, mas nao substitui extracao tabular dos artigos; por enquanto ela entra como evidência bibliografica e caminho de arquivo/DOI.",
            "Dados do Tiete ja usados no relatorio anterior entram aqui como uma subcamada contribuinte, nao como narrativa principal.",
            "Porto Primavera esta a jusante do no de Jupia; permanece na base como contexto do trecho Parana, mas nao deve ser lido como contribuinte do recorte.",
            "O inventario ANA retornou um falso positivo fora do recorte (40890000, Ribeirao Sucuriu em Tres Marias-MG, bacia do Sao Francisco); ele foi mantido no staging para auditoria, mas excluido do mapa.",
            "O filtro espacial usa o contorno esquematico da bacia; um refinamento com ottobacias oficiais ANA/IBGE pode mover estacoes e focos proximos da borda.",
        ],
        "figures": [
            {
                "id": "fig0",
                "file": "fig0_data_origin_map.svg",
                "title": "Recorte geografico: bacia contribuinte ate Jupia",
                "tag": "Mapa",
                "tag_color": "blue",
                "icon": "map",
                "summary": "Mapa esquematico do recorte: a bacia contribuinte do Alto Parana ate o outlet de Jupia, com os rios Paranaiba, Grande, Tiete e Parana como eixos estruturantes e Sucuriu/Jupia como foco local.",
                "interpretation": "A area vermelha representa o sistema que pode enviar agua, sedimentos, nutrientes e poluentes para Jupia. Os pontos ANA/Hidro sao medicoes locais; as areas coloridas indicam as sub-bacias e regioes de evidencia usadas na analise.",
                "highlight": "A unidade de analise e o sistema contribuinte ate Jupia: comportamento dos rios primeiro, poluicao e pressoes depois, correlacao no no receptor ao final.",
            },
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
                "id": "fig11",
                "file": "fig11_ana_station_series.svg",
                "title": "Series historicas ANA no eixo Sucuriu/Jupia",
                "tag": "Rios locais",
                "tag_color": "green",
                "icon": "monitoring",
                "summary": "Series mensais de vazao e cota das estacoes convencionais ANA no eixo local: Alto Sucuriu (63001500) e Sao Jose do Sucuriu (63002000) no Rio Sucuriu em Mato Grosso do Sul, e Jupia-Ponte (63005000), UHE Jupia Barramento (63007080, via SOAP) e UHE Jupia Jusante (63010000) no Rio Parana.",
                "interpretation": "Estas sao as medicoes fluviometricas locais que descem a analise da escala ONS para o rio em Mato Grosso do Sul. O Sucuriu fornece o sinal do contribuinte local; Barramento e Jusante registram o Parana no entorno da barragem. A serie SOAP do Barramento estende a cobertura local alem de 2014.",
                "highlight": (
                    f"As {station_series_summary.get('rows', 0)} medicoes mensais de {station_series_summary.get('stations', 0)} estacoes "
                    f"cobrem {station_series_summary.get('start', '')} a {station_series_summary.get('end', '')} e agora entram como camada propria de comportamento dos rios."
                    if station_series_summary
                    else "Series ANA coletadas ainda nao processadas nesta rodada."
                ),
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
            {
                "id": "fig12",
                "file": "fig12_queimadas_pressao.svg",
                "title": "Pressao territorial: focos de calor dentro da bacia contribuinte",
                "tag": "Pressoes",
                "tag_color": "red",
                "icon": "local_fire_department",
                "summary": "Focos de calor INPE/BDQueimadas por estado e ano, coletados via WFS com o envelope da bacia inteira e filtrados pelo contorno da bacia contribuinte (point-in-polygon). Cobre Mato Grosso do Sul, Sao Paulo, Minas Gerais, Goias/DF e bordas.",
                "interpretation": "Esta e a camada de pressao quantitativa do relatorio: serie anual com localizacao, agora cobrindo tambem as cabeceiras do Grande e do Paranaiba que a coleta anterior (corredor do Tiete) nao alcancava. Mato Grosso do Sul concentra o entorno de Tres Lagoas/Jupia e do Sucuriu.",
                "highlight": (
                    f"{queimadas_summary.get('total_focos', 0):,} focos dentro da bacia em {queimadas_summary.get('period', '')}; a camada de pressao agora cobre o recorte completo, nao apenas o corredor do Tiete.".replace(",", ".")
                    if queimadas_summary
                    else "Camada de queimadas nao encontrada no staging."
                ),
            },
            {
                "id": "fig13",
                "file": "fig13_qualidade_agua.svg",
                "title": "Qualidade da agua na bacia: OD, DBO, fosforo, turbidez e IQA",
                "tag": "Poluentes",
                "tag_color": "orange",
                "icon": "science",
                "summary": "Indicadores anuais de qualidade da agua da rede ANA/RNQA (medias por estacao, 1978-2021) para as estacoes dentro da bacia contribuinte, separando o eixo Mato Grosso do Sul/entorno de Jupia dos contribuintes a montante (SP/MG/GO/DF).",
                "interpretation": "O eixo poluentes deixa de depender apenas de PDFs e literatura: OD, DBO, fosforo total, turbidez, E.coli e IQA agora existem como series anuais tabuladas com coordenadas, prontas para cruzar com vazao e volume util no no receptor.",
                "highlight": (
                    f"{quality_summary.get('stations_in_basin', 0)} estacoes de qualidade dentro da bacia ({quality_summary.get('stations_ms', 0)} em MS), periodo {quality_summary.get('period', '')}; fonte ANA SNIRH ArcGIS Indicadores de Qualidade."
                    if quality_summary
                    else "Indicadores de qualidade ainda nao coletados nesta rodada."
                ),
            },
            {
                "id": "fig14",
                "file": "fig14_infoaguas_tiete_chegada.svg",
                "title": "CETESB InfoAguas: o Tiete que chega ao no de Jupia",
                "tag": "Poluentes",
                "tag_color": "orange",
                "icon": "water_ec",
                "summary": "Series mensais por coleta do CETESB InfoAguas (2000-2026) nos pontos do Baixo Tiete, com destaque para TIET02900 (Rio Tiete) e TITR02100 (Reservatorio de Tres Irmaos), as ultimas medicoes antes do Parana: OD, DBO, fosforo total e turbidez.",
                "interpretation": "Esta camada autenticada desce a granularidade de anual para mensal e estende a serie ate 2026, alem dos 129 parametros disponiveis (incluindo metais como mercurio, ferro e manganes, relevantes para sedimentos). E a ponte direta entre a poluicao do Tiete e o no receptor de Jupia.",
                "highlight": (
                    f"{infoaguas_summary.get('samples', 0):,} amostras de {len(infoaguas_summary.get('points', []))} pontos do Baixo Tiete, {infoaguas_summary.get('parameters', 0)} parametros, periodo {infoaguas_summary.get('period', '')} (coleta parcial).".replace(",", ".")
                    if infoaguas_summary
                    else "Coleta InfoAguas ainda nao disponivel."
                ),
            },
            {
                "id": "fig8",
                "file": "fig8_openalex_theme_coverage.svg",
                "title": "Cobertura academica OpenAlex por tema",
                "tag": "Fontes academicas",
                "tag_color": "green",
                "icon": "article",
                "summary": "Quantidade de trabalhos, acesso aberto e PDFs/arquivos localizados por eixo: comportamento dos rios, poluicao, sedimentos, pressao territorial, clima e correlacao integrada.",
                "interpretation": "A busca academica deixou de ser apenas bibliografia solta: ela agora aponta onde existem estudos aproveitaveis para explicar mecanismos, metodos e lacunas de dados para correlacao.",
                "highlight": f"A rodada OpenAlex retornou {openalex_context['summary'].get('works', 0)} trabalhos filtrados, com {openalex_context['summary'].get('with_pdf', 0)} caminhos de PDF/arquivo preservados.",
            },
            {
                "id": "fig9",
                "file": "fig9_openalex_timeline.svg",
                "title": "Evolucao temporal da literatura por eixo analitico",
                "tag": "Literatura",
                "tag_color": "purple",
                "icon": "timeline",
                "summary": "Serie anual de publicacoes OpenAlex agrupadas por tema, cobrindo estudos de hidrologia regional, qualidade/poluicao, sedimentos, clima e uso do solo.",
                "interpretation": "A linha do tempo ajuda a diferenciar conhecimento historico consolidado de temas mais recentes. Isso e util para decidir o que entra como contexto forte e o que ainda precisa de coleta operacional.",
                "highlight": "O relatorio passa a usar a literatura como camada de evidencias, nao como substituto dos dados oficiais de serie temporal.",
            },
            {
                "id": "fig10",
                "file": "fig10_correlation_readiness_matrix.svg",
                "title": "Matriz de prontidao para correlacao",
                "tag": "Correlacao",
                "tag_color": "orange",
                "icon": "hub",
                "summary": "Matriz qualitativa que cruza comportamento dos rios, poluicao, sedimentos, uso do solo, clima e pontos Jupia/Sucuriu com os tipos de fonte ja disponiveis.",
                "interpretation": "A correlacao so deve ser feita quando as camadas tiverem chave temporal, chave espacial e variavel comparavel. Hoje a hidrologia/operacao esta pronta, enquanto poluicao e sedimentos ainda dependem de extracao tabular de portais e PDFs.",
                "highlight": "O proximo ganho analitico vem de transformar fontes de qualidade da agua, poluicao e sedimentos em tabelas com data, local, parametro, unidade e fonte.",
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
