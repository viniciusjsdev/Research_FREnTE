"""Collect supplemental sources for the Jupia basin report.

Raw artifacts are written only under data/runs (run id prefix
``operational-supplement-jupia-``, distinct from the main collection run so the
existing context loader keeps reading inventory/series from the original run).
Downstream staging/analytic tables are produced by process_context_sources.py.

Targets:
1. ANA SNIRH ArcGIS ``SPR/Indicadores_Qualidade_v31072023`` - annual water
   quality series per station (OD, fosforo total, turbidez, E.coli, DBO, IQA),
   queried with the basin envelope.
2. INPE TerraBrasilis WFS hot spots (queimadas) with the full contributing
   basin bbox, per year, replacing the Tiete-corridor-only recorte.
3. ANA Hidro SOAP HidroSerieHistorica for station 63007080 (UHE Jupia
   Barramento, Rio Parana), the only nearby code with series in the SOAP API.
"""

from __future__ import annotations

import csv
import json
import xml.etree.ElementTree as ET
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import httpx


ROOT = Path(__file__).resolve().parents[2]
RUNS_DIR = ROOT / "data" / "runs"

# Envelope da bacia contribuinte ate Jupia (lon_min, lat_min, lon_max, lat_max).
BASIN_BBOX = (-53.3, -23.7, -44.6, -15.5)

QUALITY_BASE = "https://www.snirh.gov.br/arcgis/rest/services/SPR/Indicadores_Qualidade_v31072023/MapServer"
QUALITY_LAYERS = {
    2: ("od", "Oxigenio dissolvido (mg/L)"),
    5: ("fosforo_total", "Fosforo total (mg/L)"),
    8: ("turbidez", "Turbidez (NTU)"),
    11: ("ecoli", "E. coli (NMP/100mL)"),
    14: ("dbo", "DBO (mg/L)"),
    17: ("iqa", "Indice de Qualidade de Agua"),
}

WFS_URL = "https://terrabrasilis.dpi.inpe.br/queimadas/geoserver/wfs"
QUEIMADAS_YEARS = range(2000, 2026)

SOAP_SERIE_URL = "https://telemetriaws1.ana.gov.br/ServiceANA.asmx/HidroSerieHistorica"
SOAP_SERIES_TARGETS = [
    ("63007080", "3", "vazoes"),
    ("63007080", "1", "cotas"),
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


def parse_xml_tables(xml_text: str) -> list[dict[str, str]]:
    root = ET.fromstring(xml_text)
    rows: list[dict[str, str]] = []
    for el in root.iter():
        tag = el.tag.split("}")[-1]
        if tag in {"SerieHistorica", "Table", "Table1"}:
            row = {child.tag.split("}")[-1]: child.text or "" for child in list(el)}
            if row:
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


def collect_quality_layers(client: httpx.Client, run_dir: Path) -> list[TargetResult]:
    folder = run_dir / "collection" / "ana_arcgis_quality_indicators"
    folder.mkdir(parents=True, exist_ok=True)
    results: list[TargetResult] = []
    xmin, ymin, xmax, ymax = BASIN_BBOX
    for layer_id, (slug, label) in QUALITY_LAYERS.items():
        url = f"{QUALITY_BASE}/{layer_id}/query"
        features: list[dict[str, Any]] = []
        offset = 0
        error = ""
        while True:
            params = {
                "where": "1=1",
                "geometry": f"{xmin},{ymin},{xmax},{ymax}",
                "geometryType": "esriGeometryEnvelope",
                "inSR": "4326",
                "spatialRel": "esriSpatialRelIntersects",
                "outFields": "*",
                "returnGeometry": "false",
                "resultOffset": str(offset),
                "resultRecordCount": "1000",
                "f": "json",
            }
            try:
                response = client.get(url, params=params)
                response.raise_for_status()
                payload = response.json()
            except Exception as exc:  # noqa: BLE001 - keep collection report explicit
                error = f"{type(exc).__name__}: {exc}"
                break
            if "error" in payload:
                error = json.dumps(payload["error"])[:300]
                break
            batch = payload.get("features", [])
            features.extend(batch)
            if payload.get("exceededTransferLimit") and batch:
                offset += len(batch)
                continue
            break

        out_path = folder / f"quality_{slug}_annual_series.json"
        if error and not features:
            note_path = out_path.with_suffix(".error.txt")
            note_path.write_text(f"{error}\nURL: {url}\n", encoding="utf-8")
            results.append(TargetResult(folder.name, out_path.name, url, "arcgis_rest_query", "error", str(note_path), notes=error))
            continue
        out_path.write_text(
            json.dumps({"layer_id": layer_id, "parameter": slug, "label": label, "bbox": BASIN_BBOX, "features": features}, ensure_ascii=False),
            encoding="utf-8",
        )
        results.append(
            TargetResult(
                folder.name,
                out_path.name,
                url,
                "arcgis_rest_query",
                "collected",
                str(out_path),
                bytes=out_path.stat().st_size,
                rows=len(features),
                notes=label + (f" | partial: {error}" if error else ""),
            )
        )
        print(f"quality {slug}: {len(features)} estacoes")
    return results


def collect_queimadas(client: httpx.Client, run_dir: Path) -> list[TargetResult]:
    folder = run_dir / "collection" / "queimadas_bacia"
    folder.mkdir(parents=True, exist_ok=True)
    results: list[TargetResult] = []
    xmin, ymin, xmax, ymax = BASIN_BBOX
    for year in QUEIMADAS_YEARS:
        params = {
            "service": "WFS",
            "version": "1.0.0",
            "request": "GetFeature",
            "typeName": f"dados_abertos:focos_{year}_br_todosats",
            "bbox": f"{xmin},{ymin},{xmax},{ymax},EPSG:4326",
            "srsName": "EPSG:4326",
            "outputFormat": "CSV",
        }
        out_path = folder / f"focos_{year}_todosats.csv"
        try:
            response = client.get(WFS_URL, params=params)
            response.raise_for_status()
            text = response.text
            if text.lstrip().startswith("<"):
                raise ValueError(f"WFS exception: {text[:200]}")
            out_path.write_text(text, encoding="utf-8")
            n_rows = max(text.count("\n") - 1, 0)
            results.append(
                TargetResult(folder.name, out_path.name, str(response.url), "wfs_getfeature_csv", "collected", str(out_path), bytes=len(response.content), rows=n_rows)
            )
            print(f"queimadas {year}: {n_rows} focos")
        except Exception as exc:  # noqa: BLE001
            note_path = out_path.with_suffix(".error.txt")
            note_path.write_text(f"{type(exc).__name__}: {exc}\n", encoding="utf-8")
            results.append(TargetResult(folder.name, out_path.name, WFS_URL, "wfs_getfeature_csv", "error", str(note_path), notes=str(exc)[:300]))
            print(f"queimadas {year}: ERRO {exc}")
    return results


def collect_soap_series(client: httpx.Client, run_dir: Path) -> list[TargetResult]:
    folder = run_dir / "collection" / "ana_hidro_soap_series"
    folder.mkdir(parents=True, exist_ok=True)
    results: list[TargetResult] = []
    for code, tipo, label in SOAP_SERIES_TARGETS:
        params = {
            "codEstacao": code,
            "dataInicio": "01/01/1900",
            "dataFim": "31/12/2026",
            "tipoDados": tipo,
            "nivelConsistencia": "",
        }
        xml_path = folder / f"{code}_{label}.xml"
        csv_path = folder / f"{code}_{label}.csv"
        try:
            response = client.post(SOAP_SERIE_URL, data=params)
            response.raise_for_status()
            xml_path.write_bytes(response.content)
            rows = parse_xml_tables(response.text)
            save_rows_csv(csv_path, rows)
            results.append(
                TargetResult(folder.name, csv_path.name, SOAP_SERIE_URL, "soap_http_post", "collected", str(csv_path), bytes=len(response.content), rows=len(rows), notes=f"params: {params}")
            )
            print(f"soap {code} {label}: {len(rows)} registros")
        except Exception as exc:  # noqa: BLE001
            note_path = xml_path.with_suffix(".error.txt")
            note_path.write_text(f"{type(exc).__name__}: {exc}\n", encoding="utf-8")
            results.append(TargetResult(folder.name, xml_path.name, SOAP_SERIE_URL, "soap_http_post", "error", str(note_path), notes=str(exc)[:300]))
    return results


def main() -> None:
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
    run_id = f"operational-supplement-jupia-{timestamp}"
    run_dir = RUNS_DIR / run_id
    run_dir.mkdir(parents=True, exist_ok=True)

    results: list[TargetResult] = []
    with httpx.Client(timeout=httpx.Timeout(300, connect=60), follow_redirects=True) as client:
        results.extend(collect_quality_layers(client, run_dir))
        results.extend(collect_soap_series(client, run_dir))
        results.extend(collect_queimadas(client, run_dir))

    collected = [r for r in results if r.status == "collected"]
    manifest = {
        "run_id": run_id,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "purpose": "Supplemental Jupia collection: ANA quality indicators (ArcGIS), basin-wide INPE hot spots, SOAP series 63007080.",
        "basin_bbox": BASIN_BBOX,
        "summary": {
            "targets_total": len(results),
            "collected": len(collected),
            "errors": len(results) - len(collected),
            "quality_layers": sum(1 for r in collected if r.source_slug == "ana_arcgis_quality_indicators"),
            "queimadas_years": sum(1 for r in collected if r.source_slug == "queimadas_bacia"),
            "soap_series": sum(1 for r in collected if r.source_slug == "ana_hidro_soap_series"),
        },
        "results": [asdict(r) for r in results],
    }
    (run_dir / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(manifest["summary"], indent=2))
    print(f"run: {run_dir}")


if __name__ == "__main__":
    main()
