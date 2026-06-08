"""Collect operational source artifacts for the Jupia basin run.

Raw artifacts are written only under data/runs. Downstream staging/analytic
tables are produced by process_context_sources.py.
"""

from __future__ import annotations

import csv
import json
import re
import unicodedata
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import httpx
import pandas as pd


ROOT = Path(__file__).resolve().parents[2]
RUNS_DIR = ROOT / "data" / "runs"
STAGING_DIR = ROOT / "data" / "staging" / "jupia_bacia"
ANALYTIC_DIR = ROOT / "data" / "analytic" / "jupia_bacia"
DISCOVERY_RUN_ID = "perplexity-intel-58d59340"
SOAP_URL = "https://telemetriaws1.ana.gov.br/ServiceANA.asmx/HidroInventario"
GITHUB_RAW = "https://raw.githubusercontent.com/anagovbr/hidro-dados-estacoes-convencionais/dev"

STATION_CODES_OF_INTEREST = [
    "62019900",
    "62916000",
    "63001850",
    "63002000",
    "63003200",
    "63003300",
    "63003400",
    "63004000",
    "63005000",
    "63007070",
    "63007080",
    "63010000",
    "63015000",
]


@dataclass
class TargetResult:
    source_slug: str
    dataset_name: str
    url: str
    method: str
    status: str
    output_path: str = ""
    bytes: int = 0
    rows: int | None = None
    notes: str = ""


def ascii_key(value: object) -> str:
    text = str(value or "")
    text = text.replace("�", " ")
    text = unicodedata.normalize("NFKD", text)
    text = "".join(ch for ch in text if not unicodedata.combining(ch))
    return re.sub(r"\s+", " ", text).strip().upper()


def safe_filename(value: str, suffix: str) -> str:
    name = ascii_key(value).lower()
    name = re.sub(r"[^a-z0-9]+", "-", name).strip("-")
    return f"{name}{suffix}"


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def parse_xml_tables(xml_text: str) -> list[dict[str, str]]:
    root = ET.fromstring(xml_text)
    rows: list[dict[str, str]] = []
    for el in root.iter():
        tag = el.tag.split("}")[-1]
        if tag in {"Table", "Table1"}:
            row = {child.tag.split("}")[-1]: child.text or "" for child in list(el)}
            if "Vazio" not in row:
                rows.append(row)
    return rows


def save_rows_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        path.write_text("", encoding="utf-8")
        return
    fields = sorted({key for row in rows for key in row})
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def download(client: httpx.Client, url: str, out_path: Path) -> TargetResult:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    try:
        response = client.get(url)
        response.raise_for_status()
        out_path.write_bytes(response.content)
        return TargetResult(
            source_slug=out_path.parent.name,
            dataset_name=out_path.name,
            url=url,
            method="direct_download",
            status="collected",
            output_path=str(out_path),
            bytes=len(response.content),
        )
    except Exception as exc:  # noqa: BLE001 - keep collection report explicit
        note_path = out_path.with_suffix(out_path.suffix + ".error.txt")
        note_path.write_text(f"{type(exc).__name__}: {exc}\nURL: {url}\n", encoding="utf-8")
        return TargetResult(
            source_slug=out_path.parent.name,
            dataset_name=out_path.name,
            url=url,
            method="direct_download",
            status="error",
            output_path=str(note_path),
            notes=str(exc),
        )


def collect_soap_inventory(client: httpx.Client, run_dir: Path) -> tuple[list[TargetResult], list[dict[str, Any]]]:
    base_params = {
        "codEstDE": "",
        "codEstATE": "",
        "tpEst": "",
        "nmEst": "",
        "nmRio": "",
        "codSubBacia": "",
        "codBacia": "",
        "nmMunicipio": "",
        "nmEstado": "",
        "sgResp": "",
        "sgOper": "",
        "telemetrica": "",
    }
    queries = [
        ("station_name_jupia_accent", {"nmEst": "JUPIÁ"}),
        ("station_name_jupia_ascii", {"nmEst": "JUPIA"}),
        ("station_name_sucuriu", {"nmEst": "SUCURIU"}),
        ("river_name_sucuriu", {"nmRio": "SUCURIU"}),
    ]
    folder = run_dir / "collection" / "ana_hidro_soap_inventory"
    results: list[TargetResult] = []
    all_rows: list[dict[str, Any]] = []

    for label, override in queries:
        params = {**base_params, **override}
        output_xml = folder / f"{label}.xml"
        try:
            response = client.post(SOAP_URL, data=params)
            response.raise_for_status()
            output_xml.parent.mkdir(parents=True, exist_ok=True)
            output_xml.write_bytes(response.content)
            rows = parse_xml_tables(response.text)
            for row in rows:
                row["source_query"] = label
                row["requested_filter"] = json.dumps(override, ensure_ascii=False)
            all_rows.extend(rows)
            results.append(
                TargetResult(
                    source_slug=folder.name,
                    dataset_name=label,
                    url=SOAP_URL,
                    method="soap_http_post",
                    status="collected",
                    output_path=str(output_xml),
                    bytes=len(response.content),
                    rows=len(rows),
                    notes=f"SOAP query params: {override}",
                )
            )
        except Exception as exc:  # noqa: BLE001
            note_path = output_xml.with_suffix(".error.txt")
            note_path.write_text(f"{type(exc).__name__}: {exc}\n", encoding="utf-8")
            results.append(
                TargetResult(
                    source_slug=folder.name,
                    dataset_name=label,
                    url=SOAP_URL,
                    method="soap_http_post",
                    status="error",
                    output_path=str(note_path),
                    notes=str(exc),
                )
            )

    dedup: dict[tuple[str, str], dict[str, Any]] = {}
    for row in all_rows:
        key = (str(row.get("Codigo", "")), str(row.get("source_query", "")))
        dedup[key] = row
    rows = list(dedup.values())
    save_rows_csv(folder / "station_inventory_matches.csv", rows)
    return results, rows


def collect_station_series(client: httpx.Client, run_dir: Path, codes: list[str]) -> tuple[list[TargetResult], list[dict[str, Any]]]:
    folder = run_dir / "collection" / "ana_github_hidro_series"
    results: list[TargetResult] = []
    coverage_rows: list[dict[str, Any]] = []

    metadata_urls = [
        f"{GITHUB_RAW}/Descricao_Arquivos_Dados.csv",
        f"{GITHUB_RAW}/Inventario_Estacoes_Hidrologicas_04-08-2023.csv",
    ]
    for url in metadata_urls:
        results.append(download(client, url, folder / Path(url).name))

    for code in codes:
        for kind in ("cotas", "vazoes"):
            filename = f"{code}_{kind}.csv"
            url = f"{GITHUB_RAW}/fluviometricas/csv/{code}/{filename}"
            out_path = folder / code / filename
            result = download(client, url, out_path)
            results.append(result)
            if result.status != "collected":
                coverage_rows.append(
                    {
                        "station_code": code,
                        "series_type": kind,
                        "status": result.status,
                        "rows": 0,
                        "period_start": "",
                        "period_end": "",
                        "source_path": result.output_path,
                        "notes": result.notes,
                    }
                )
                continue
            try:
                df = pd.read_csv(out_path, sep=";", encoding="utf-8", low_memory=False)
                dates = pd.to_datetime(df.get("Data"), dayfirst=True, errors="coerce")
                coverage_rows.append(
                    {
                        "station_code": code,
                        "series_type": kind,
                        "status": "collected",
                        "rows": int(len(df)),
                        "period_start": str(dates.min().date()) if dates.notna().any() else "",
                        "period_end": str(dates.max().date()) if dates.notna().any() else "",
                        "source_path": str(out_path),
                        "notes": "ANA GitHub branch dev, conventional hydrological stations",
                    }
                )
            except Exception as exc:  # noqa: BLE001
                coverage_rows.append(
                    {
                        "station_code": code,
                        "series_type": kind,
                        "status": "collected_unparsed",
                        "rows": 0,
                        "period_start": "",
                        "period_end": "",
                        "source_path": str(out_path),
                        "notes": str(exc),
                    }
                )

    save_rows_csv(run_dir / "processing" / "02-station-series-coverage.csv", coverage_rows)
    return results, coverage_rows


def collect_context_documents(client: httpx.Client, run_dir: Path) -> list[TargetResult]:
    folder = run_dir / "collection" / "context_quality_pollution_documents"
    targets = [
        (
            "ibge_bacias_nivel_3.xlsx",
            "https://geoftp.ibge.gov.br/informacoes_ambientais/estudos_ambientais/bacias_e_divisoes_hidrograficas_do_brasil/2021/Bacias_Hidrograficas_do_Brasil_BHB250/tabelas/bacias_nivel_3.xlsx",
        ),
        (
            "cetesb_qualidade_aguas_interiores_2008.pdf",
            "https://repositorio.cetesb.sp.gov.br/server/api/core/bitstreams/082c95e3-2e0b-424c-bbec-fab8c4aa8c00/content",
        ),
        (
            "cetesb_qualidade_aguas_interiores_sp.pdf",
            "https://repositorio.cetesb.sp.gov.br/server/api/core/bitstreams/5380522b-44ba-41c6-b530-99147e5fe132/content",
        ),
        (
            "cbh_tiete_batalha_situacao_2023_2024.pdf",
            "https://www.comitetb.sp.gov.br/download/servico/deliberacao/RS%202023-2024%20TB%20vers%C3%A3o%20final%2006%20dez%202024.pdf",
        ),
        (
            "ana_atlas_esgotos_release.pdf",
            "https://www.ana.gov.br/atlasesgotos/Release.Atlas.Esgotos.pdf",
        ),
        (
            "ana_rede_nacional_qualidade_agua.html",
            "https://www.gov.br/ana/pt-br/assuntos/monitoramento-e-eventos-criticos/qualidade-da-agua",
        ),
        (
            "cetesb_simqua_inicio.html",
            "https://simqua.cetesb.sp.gov.br/webgis/inicio",
        ),
    ]
    return [download(client, url, folder / name) for name, url in targets]


def build_manifest(
    run_id: str,
    run_dir: Path,
    results: list[TargetResult],
    station_rows: list[dict[str, Any]],
    coverage_rows: list[dict[str, Any]],
) -> dict[str, Any]:
    requested_station_rows = [
        row
        for row in station_rows
        if "JUPI" in ascii_key(row.get("Nome")) and "SUCURI" in ascii_key(row.get("Nome"))
    ]
    collected_series = [row for row in coverage_rows if row.get("status") == "collected"]
    return {
        "run_id": run_id,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "scope": {
            "study": "Bacia Hidrografica de Jupia",
            "requested_station": "UHE JUPIA SUCURIU",
            "geographic_scope": "Alto Parana / UHE Jupia, Rio Sucuriu, Rio Tiete, Rio Grande, Rio Paranaiba, Rio Parana; SP, MS, MG, GO e DF como bacia contribuinte ampliada.",
            "discovery_run_id": DISCOVERY_RUN_ID,
            "target_window_years": 20,
        },
        "summary": {
            "targets_total": len(results),
            "collected": sum(1 for item in results if item.status == "collected"),
            "errors": sum(1 for item in results if item.status == "error"),
            "station_inventory_rows": len(station_rows),
            "requested_station_matches": len(requested_station_rows),
            "station_series_collected": len(collected_series),
        },
        "requested_station_matches": requested_station_rows,
        "results": [item.__dict__ for item in results],
        "outputs": {
            "collection_targets": str(run_dir / "reports" / "collection_targets.csv"),
            "station_inventory_matches": str(run_dir / "collection" / "ana_hidro_soap_inventory" / "station_inventory_matches.csv"),
            "station_series_coverage": str(run_dir / "processing" / "02-station-series-coverage.csv"),
        },
    }


def write_reports(run_id: str, run_dir: Path, manifest: dict[str, Any], results: list[TargetResult]) -> None:
    reports_dir = run_dir / "reports"
    reports_dir.mkdir(parents=True, exist_ok=True)
    save_rows_csv(reports_dir / "collection_targets.csv", [item.__dict__ for item in results])
    requested = manifest["requested_station_matches"]
    md = [
        f"# Coleta operacional Jupia - {run_id}",
        "",
        "## Escopo",
        manifest["scope"]["geographic_scope"],
        "",
        "## Resultado",
        f"- Alvos tentados: {manifest['summary']['targets_total']}",
        f"- Coletados: {manifest['summary']['collected']}",
        f"- Erros/bloqueios: {manifest['summary']['errors']}",
        f"- Linhas de inventario de estacoes: {manifest['summary']['station_inventory_rows']}",
        f"- Matches diretos para UHE JUPIA SUCURIU: {manifest['summary']['requested_station_matches']}",
        f"- Series historicas ANA/GitHub coletadas: {manifest['summary']['station_series_collected']}",
        "",
        "## Estacao solicitada",
    ]
    if requested:
        for row in requested:
            md.append(
                "- "
                + "; ".join(
                    [
                        f"codigo={row.get('Codigo', '')}",
                        f"nome={row.get('Nome', '')}",
                        f"rio={row.get('RioNome', '')}",
                        f"municipio={row.get('nmMunicipio', '')}",
                        f"uf={row.get('nmEstado', '')}",
                        f"lat={row.get('Latitude', '')}",
                        f"lon={row.get('Longitude', '')}",
                    ]
                )
            )
    else:
        md.append("- Nenhum match direto encontrado no inventario SOAP publico.")
    md.extend(
        [
            "",
            "## Observacoes",
            "- HidroWeb REST respondeu 401 sem credencial durante a exploracao; a coleta usou SOAP publico e repositório ANA/GitHub quando disponivel.",
            "- Codigos com inventario podem nao ter CSV historico no branch dev do repositorio ANA.",
            "- Documentos de qualidade/poluicao foram preservados como bruto para extracao posterior.",
        ]
    )
    (reports_dir / f"{run_id}.md").write_text("\n".join(md) + "\n", encoding="utf-8")


def main() -> None:
    run_id = "operational-collect-jupia-" + datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
    run_dir = RUNS_DIR / run_id
    for subdir in ("config", "collection", "processing", "reports"):
        (run_dir / subdir).mkdir(parents=True, exist_ok=True)

    options = {
        "source": "manual operational collector",
        "discovery_run_id": DISCOVERY_RUN_ID,
        "requested_station": "UHE JUPIA SUCURIU",
        "station_codes_of_interest": STATION_CODES_OF_INTEREST,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    write_json(run_dir / "config" / "collection-options.json", options)

    timeout = httpx.Timeout(90.0, connect=30.0)
    headers = {"User-Agent": "Research-FREnTE-Jupia-Collector/1.0"}
    with httpx.Client(timeout=timeout, follow_redirects=True, headers=headers) as client:
        results: list[TargetResult] = []
        soap_results, station_rows = collect_soap_inventory(client, run_dir)
        results.extend(soap_results)

        discovered_codes = sorted(
            {str(row.get("Codigo", "")).strip() for row in station_rows if str(row.get("Codigo", "")).strip()}
            | set(STATION_CODES_OF_INTEREST)
        )
        series_results, coverage_rows = collect_station_series(client, run_dir, discovered_codes)
        results.extend(series_results)
        results.extend(collect_context_documents(client, run_dir))

    save_rows_csv(run_dir / "processing" / "01-collection-targets.csv", [item.__dict__ for item in results])
    write_json(run_dir / "processing" / "01-collection-targets.json", [item.__dict__ for item in results])
    manifest = build_manifest(run_id, run_dir, results, station_rows, coverage_rows)
    write_json(run_dir / "manifest.json", manifest)
    write_reports(run_id, run_dir, manifest, results)
    print(json.dumps({"run_id": run_id, "run_dir": str(run_dir), "summary": manifest["summary"]}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
