"""CLI entrypoint para o fluxo principal de pesquisa via Perplexity."""

from __future__ import annotations

import argparse
import json
from datetime import datetime
from pathlib import Path
from typing import Any

from src.utils.io import write_catalog_csv
from src.utils.logging import configure_logging

try:
    from src.connectors.operational_dataset_collector import AVAILABLE_OPERATIONAL_TARGETS, DEFAULT_TIETE_BBOX
    from src.pipelines.operational_dataset_collection_pipeline import OperationalDatasetCollectionPipeline
except ImportError:  # pragma: no cover - depende do ambiente local
    AVAILABLE_OPERATIONAL_TARGETS = (
        "infoaguas_qualidade_agua",
        "bdqueimadas_focos_calor",
        "snis_agua_esgoto",
        "cetesb_inventario_residuos",
    )
    DEFAULT_TIETE_BBOX = (-52.2, -24.0, -45.8, -20.5)
    OperationalDatasetCollectionPipeline = None

try:
    from src.pipelines.perplexity_intelligence_pipeline import PerplexityIntelligencePipeline
except ImportError:  # pragma: no cover - depende do ambiente local
    PerplexityIntelligencePipeline = None

REPO_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_CONTEXT_FILE = REPO_ROOT / "config" / "context_100k.yaml"
DEFAULT_TRACKS_FILE = REPO_ROOT / "config" / "tracks_100k.yaml"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="research-frente")
    subparsers = parser.add_subparsers(dest="command", required=True)

    run_parser = subparsers.add_parser(
        "run",
        help="Executa o fluxo principal: contexto mestre + chats tematicos no Perplexity",
    )
    _add_perplexity_args(run_parser)

    perplexity_parser = subparsers.add_parser(
        "perplexity-intel",
        help="Alias explicito para o fluxo principal via Perplexity",
    )
    _add_perplexity_args(perplexity_parser)

    export_parser = subparsers.add_parser("export", help="Exporta catalogo JSON para CSV")
    export_parser.add_argument("--catalog", required=True, help="Caminho para o catalog.json")
    export_parser.add_argument("--output", required=True, help="Caminho de saida CSV")

    collect_parser = subparsers.add_parser(
        "collect-operational",
        help="Coleta dados operacionais brutos para acoplamento na EDA de reservatorios",
    )
    _add_collect_operational_args(collect_parser)

    return parser


def _add_perplexity_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--query", required=True, help="Tema base da pesquisa")
    parser.add_argument("--limit", type=int, default=20, help="Limite de datasets/fontes normalizadas")
    parser.add_argument("--max-searches", type=int, default=5, help="Quantidade maxima de chats tematicos")
    parser.add_argument(
        "--search-provider",
        choices=["perplexity", "perplexity-openalex", "openalex"],
        default="perplexity",
        help="Fonte de busca: Perplexity, Perplexity + OpenAlex ou apenas OpenAlex.",
    )
    parser.add_argument(
        "--perplexity-max-results",
        type=int,
        default=20,
        help="Numero maximo de resultados por busca na Search API (1-20).",
    )
    parser.add_argument(
        "--perplexity-timeout",
        type=float,
        default=60.0,
        help="Timeout em segundos das chamadas a API do Perplexity.",
    )
    parser.add_argument(
        "--openalex-mode",
        choices=["academic", "all"],
        default="academic",
        help="Trilhas enviadas a OpenAlex quando o provedor inclui OpenAlex.",
    )
    parser.add_argument(
        "--openalex-max-results",
        type=int,
        default=25,
        help="Numero maximo de trabalhos por busca na OpenAlex (1-100).",
    )
    parser.add_argument(
        "--openalex-timeout",
        type=float,
        default=60.0,
        help="Timeout em segundos das chamadas a API OpenAlex.",
    )
    parser.add_argument(
        "--openalex-from-year",
        type=int,
        help="Ano inicial de publicacao para filtrar trabalhos OpenAlex.",
    )
    parser.add_argument(
        "--openalex-to-year",
        type=int,
        help="Ano final de publicacao para filtrar trabalhos OpenAlex.",
    )
    parser.add_argument(
        "--context-file",
        help="Arquivo JSON ou YAML com o contexto mestre da pesquisa.",
    )
    parser.add_argument(
        "--tracks-file",
        help="Arquivo JSON ou YAML com as trilhas/chats tematicos.",
    )
    parser.add_argument(
        "--track-limit",
        type=int,
        help="Limita quantas trilhas do arquivo de tracks serao executadas nesta rodada.",
    )
    parser.add_argument(
        "--llm-mode",
        choices=["auto", "off", "openai"],
        default="auto",
        help="Modo de inferencia para classificar fontes. 'auto' usa OpenAI se houver chave configurada.",
    )
    parser.add_argument(
        "--llm-model",
        default="gpt-4.1-nano",
        help="Modelo OpenAI usado na inferencia estrutural das fontes.",
    )
    parser.add_argument(
        "--llm-timeout",
        type=float,
        default=60.0,
        help="Timeout das chamadas de inferencia por LLM.",
    )
    parser.add_argument(
        "--llm-fail-on-error",
        action="store_true",
        help="Interrompe a execucao se a inferencia por LLM falhar.",
    )
    parser.add_argument(
        "--skip-collection-guides",
        action="store_true",
        default=False,
        help="Pular extracao de guias de coleta via Firecrawl (economiza creditos).",
    )


def _add_collect_operational_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--target",
        action="append",
        choices=list(AVAILABLE_OPERATIONAL_TARGETS),
        help="Target operacional a coletar. Se omitido, coleta todos os targets configurados.",
    )
    parser.add_argument(
        "--year-start",
        type=int,
        default=2000,
        help="Ano inicial da janela de coleta.",
    )
    parser.add_argument(
        "--year-end",
        type=int,
        default=datetime.now().year,
        help="Ano final da janela de coleta.",
    )
    parser.add_argument(
        "--bbox",
        default=",".join(str(value) for value in DEFAULT_TIETE_BBOX),
        help="Bounding box no formato min_lon,min_lat,max_lon,max_lat para filtros geograficos.",
    )
    parser.add_argument(
        "--bdqueimadas-series",
        choices=["satref", "todosats"],
        default="todosats",
        help="Serie do BDQueimadas usada na exportacao WFS.",
    )


def run(argv: list[str] | None = None) -> int:
    configure_logging()
    _load_dotenv_if_available()
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.command == "export":
        return _run_export(catalog_path=Path(args.catalog), output_path=Path(args.output))
    if args.command == "collect-operational":
        return _run_collect_operational(args)
    return _run_perplexity_intel(args)


def _run_perplexity_intel(args: argparse.Namespace) -> int:
    import os

    pipeline_cls = PerplexityIntelligencePipeline
    if pipeline_cls is None:
        try:
            from src.pipelines.perplexity_intelligence_pipeline import PerplexityIntelligencePipeline as pipeline_cls
        except ImportError as exc:
            print(f"Erro: dependencias do fluxo Perplexity indisponiveis: {exc}")
            return 1

    perplexity_api_key = os.getenv("PERPLEXITY_API_KEY", "").strip()
    firecrawl_api_key = os.getenv("FIRECRAWL_API_KEY", "").strip()
    openalex_api_key = os.getenv("OPENALEX_API_KEY", "").strip()
    openalex_mailto = os.getenv("OPENALEX_MAILTO", "").strip()

    perplexity_enabled = args.search_provider in {"perplexity", "perplexity-openalex"}
    openalex_mode = args.openalex_mode if args.search_provider in {"perplexity-openalex", "openalex"} else "off"

    if perplexity_enabled and not perplexity_api_key:
        print("Erro: PERPLEXITY_API_KEY nao configurada no ambiente.")
        return 1

    master_context_payload = _resolve_structured_payload(args.context_file, DEFAULT_CONTEXT_FILE)
    research_tracks_payload = _resolve_structured_payload(args.tracks_file, DEFAULT_TRACKS_FILE)
    if isinstance(research_tracks_payload, list) and args.track_limit:
        research_tracks_payload = research_tracks_payload[: max(args.track_limit, 0)]

    result = pipeline_cls(
        base_query=args.query,
        limit=args.limit,
        max_searches=args.max_searches,
        perplexity_api_key=perplexity_api_key,
        perplexity_enabled=perplexity_enabled,
        perplexity_max_results=args.perplexity_max_results,
        perplexity_timeout_seconds=args.perplexity_timeout,
        openalex_mode=openalex_mode,
        openalex_max_results=args.openalex_max_results,
        openalex_timeout_seconds=args.openalex_timeout,
        openalex_api_key=openalex_api_key,
        openalex_mailto=openalex_mailto,
        openalex_from_publication_year=args.openalex_from_year,
        openalex_to_publication_year=args.openalex_to_year,
        master_context_payload=master_context_payload,
        research_tracks_payload=research_tracks_payload,
        llm_mode=args.llm_mode,
        llm_model=args.llm_model,
        llm_timeout_seconds=args.llm_timeout,
        llm_fail_on_error=args.llm_fail_on_error,
        firecrawl_api_key=firecrawl_api_key,
        skip_collection_guides=args.skip_collection_guides,
    ).execute()

    print(f"Research ID: {result['research_id']}")
    print(f"Master context: {result['master_context_path']}")
    print(f"Filtered sources: {result['filtered_source_count']}")
    print(f"Enriched datasets: {result['enriched_dataset_count']}")
    print(f"Ranked datasets: {result['ranked_dataset_count']}")
    print(f"Collection guides: {result['collection_guide_count']}")
    print(f"Manifest: {result['intelligence_path']}")
    print(f"Report: {result['report_path']}")
    print(f"Sources CSV: {result['sources_csv_path']}")
    print(f"Datasets CSV: {result['datasets_csv_path']}")
    return 0


def _run_export(catalog_path: Path, output_path: Path) -> int:
    payload = json.loads(catalog_path.read_text(encoding="utf-8"))
    rows = [
        {
            "dataset_id": item["dataset_id"],
            "title": item["title"],
            "source_name": item["source_name"],
            "source_url": item["source_url"],
            "relevance_score": item["relevance_score"],
            "access_level": item["access_level"],
            "priority": item.get("priority", "unknown"),
            "dataset_kind": item.get("dataset_kind", "unknown"),
            "methodological_note": " | ".join(item.get("methodological_notes", [])[:1]),
        }
        for item in payload.get("datasets", [])
    ]
    write_catalog_csv(output_path, rows)
    print(f"Exportado CSV em: {output_path}")
    return 0


def _run_collect_operational(args: argparse.Namespace) -> int:
    pipeline_cls = OperationalDatasetCollectionPipeline
    if pipeline_cls is None:
        try:
            from src.pipelines.operational_dataset_collection_pipeline import (
                OperationalDatasetCollectionPipeline as pipeline_cls,
            )
        except ImportError as exc:
            print(f"Erro: dependencias da coleta operacional indisponiveis: {exc}")
            return 1

    if args.year_end < args.year_start:
        print("Erro: --year-end deve ser maior ou igual a --year-start.")
        return 1

    pipeline = pipeline_cls(
        target_ids=args.target or list(AVAILABLE_OPERATIONAL_TARGETS),
        year_start=args.year_start,
        year_end=args.year_end,
        bbox=_parse_bbox(args.bbox),
        bdqueimadas_series=args.bdqueimadas_series,
    )
    result = pipeline.execute()

    print(f"Run ID: {result['run_id']}")
    print(f"Run dir: {result['run_dir']}")
    print(f"Targets: {result['target_count']}")
    print(f"Collected: {result['collected_count']}")
    print(f"Partial: {result['partial_count']}")
    print(f"Blocked: {result['blocked_count']}")
    print(f"Errors: {result['error_count']}")
    print(f"Manifest: {result['manifest_path']}")
    print(f"Processing: {result['processing_path']}")
    print(f"Report: {result['report_path']}")
    print(f"Report CSV: {result['report_csv_path']}")
    return 0


def _load_structured_file(path_str: str) -> Any:
    path = Path(path_str)
    raw = path.read_text(encoding="utf-8")
    suffix = path.suffix.lower()
    if suffix == ".json":
        return json.loads(raw)
    try:
        import yaml
    except ImportError as exc:  # pragma: no cover - depende do ambiente local
        raise RuntimeError("PyYAML nao esta disponivel para ler arquivos YAML.") from exc
    return yaml.safe_load(raw)


def _resolve_structured_payload(explicit_path: str | None, default_path: Path) -> Any:
    if explicit_path:
        return _load_structured_file(explicit_path)
    if default_path.exists():
        return _load_structured_file(str(default_path))
    return None


def _parse_bbox(raw_value: str) -> tuple[float, float, float, float]:
    parts = [item.strip() for item in raw_value.split(",") if item.strip()]
    if len(parts) != 4:
        raise ValueError("BBox deve ter quatro valores separados por virgula.")
    return tuple(float(item) for item in parts)  # type: ignore[return-value]


def _load_dotenv_if_available() -> None:
    try:
        from dotenv import load_dotenv
    except ImportError:  # pragma: no cover - depende do ambiente local
        return
    load_dotenv()


if __name__ == "__main__":
    raise SystemExit(run())
