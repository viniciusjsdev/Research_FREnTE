"""Pipeline principal de pesquisa para artigo via Perplexity API."""

from __future__ import annotations

import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable
from uuid import uuid4

from src.agents.enrich_agent import EnrichAgent
from src.agents.filter_validate_agent import FilterValidateAgent
from src.agents.rank_access_agent import RankAccessAgent
from src.agents.report_agent import ReportAgent
from src.connectors.firecrawl_collector import FirecrawlCollector
from src.connectors.llm import LLMConnector, LLMConnectorError, OpenAIResponsesConnector
from src.connectors.openalex_api import OpenAlexAPICollector
from src.connectors.perplexity_api import PerplexityAPICollector
from src.schemas.records import (
    PerplexityResearchContextRecord,
    PerplexityResearchTrackRecord,
    PerplexitySearchQueryRecord,
)
from src.schemas.settings import PipelineSettings
from src.generators.html_report_generator import generate_html_report
from src.utils.io import ensure_dir, write_catalog_csv, write_json, write_markdown


class PerplexityIntelligencePipeline:
    """Executa o fluxo principal: contexto mestre, chats tematicos e consolidado de inteligencia."""

    DEFAULT_RESEARCH_TRACKS = (
        {
            "research_track": "official_data_portals",
            "chat_label": "chat-portais-oficiais",
            "search_profile": "official_portals",
            "target_intent": "dataset_discovery",
            "research_question": "Quais portais oficiais e fontes primarias concentram dados relevantes para esta pesquisa?",
            "task_prompt": (
                "Procure ministerios, agencias, institutos, catalogos, APIs, paineis e portais de dados "
                "diretamente relacionados ao tema da pesquisa."
            ),
            "priority": "high",
        },
        {
            "research_track": "monitoring_and_measurements",
            "chat_label": "chat-monitoramento",
            "search_profile": "monitoring_sources",
            "target_intent": "dataset_discovery",
            "research_question": "Quais fontes trazem monitoramento, series historicas e medidas recorrentes sobre o tema?",
            "task_prompt": (
                "Busque programas de monitoramento, series historicas, sensores, estacoes, indicadores e "
                "bases recorrentes ligadas ao objeto de estudo."
            ),
            "priority": "high",
        },
        {
            "research_track": "pressure_and_drivers",
            "chat_label": "chat-pressoes-e-vetores",
            "search_profile": "pressure_drivers",
            "target_intent": "dataset_discovery",
            "research_question": "Quais datasets ajudam a explicar vetores, pressoes e mudancas associadas ao tema?",
            "task_prompt": (
                "Procure bases sobre uso do territorio, ocupacao, pressao antropica, infraestruturas, "
                "saneamento, queimadas, cobertura do solo ou outros vetores relevantes ao tema."
            ),
            "priority": "medium",
        },
        {
            "research_track": "institutional_reports",
            "chat_label": "chat-relatorios-institucionais",
            "search_profile": "institutional_reports",
            "target_intent": "contextual_intelligence",
            "research_question": "Quais relatorios tecnicos e documentos institucionais ajudam a contextualizar a pesquisa?",
            "task_prompt": (
                "Procure relatorios tecnicos, planos, diagnosticos, boletins e documentos institucionais "
                "que ajudem a entender o contexto e apontem para fontes de dados."
            ),
            "priority": "medium",
        },
        {
            "research_track": "academic_knowledge",
            "chat_label": "chat-literatura-academica",
            "search_profile": "academic_knowledge",
            "target_intent": "academic_knowledge",
            "research_question": "Quais artigos, teses e repositorios academicos citam dados ou metodologias relevantes?",
            "task_prompt": (
                "Procure artigos, teses, revisoes e repositorios academicos que citem bases de dados, "
                "monitoramentos, protocolos ou abordagens metodologicas aproveitaveis."
            ),
            "priority": "medium",
        },
    )

    def __init__(
        self,
        *,
        base_query: str,
        limit: int = 20,
        max_searches: int = 5,
        perplexity_api_key: str = "",
        perplexity_enabled: bool = True,
        perplexity_max_results: int = 20,
        perplexity_timeout_seconds: float = 60.0,
        openalex_mode: str = "off",
        openalex_max_results: int = 25,
        openalex_timeout_seconds: float = 60.0,
        openalex_api_key: str = "",
        openalex_mailto: str = "",
        openalex_from_publication_year: int | None = None,
        openalex_to_publication_year: int | None = None,
        master_context_payload: dict[str, Any] | None = None,
        research_tracks_payload: list[dict[str, Any]] | None = None,
        llm_mode: str = "auto",
        llm_model: str = "gpt-4.1-nano",
        llm_timeout_seconds: float = 60.0,
        llm_fail_on_error: bool = False,
        firecrawl_api_key: str = "",
        firecrawl_timeout_seconds: float = 60.0,
        skip_collection_guides: bool = False,
        llm_connector: LLMConnector | None = None,
        collector_factory: Callable[[], Any] | None = None,
        openalex_collector_factory: Callable[[], Any] | None = None,
        firecrawl_collector_factory: Callable[[], Any] | None = None,
    ) -> None:
        self.base_query = base_query
        self.limit = limit
        self.max_searches = max_searches
        self.perplexity_api_key = perplexity_api_key
        self.perplexity_enabled = perplexity_enabled
        self.perplexity_max_results = perplexity_max_results
        self.perplexity_timeout_seconds = perplexity_timeout_seconds
        self.openalex_mode = openalex_mode
        self.openalex_max_results = openalex_max_results
        self.openalex_timeout_seconds = openalex_timeout_seconds
        self.openalex_api_key = openalex_api_key
        self.openalex_mailto = openalex_mailto
        self.openalex_from_publication_year = openalex_from_publication_year
        self.openalex_to_publication_year = openalex_to_publication_year
        self.master_context_payload = master_context_payload
        self.research_tracks_payload = research_tracks_payload
        self.llm_mode = llm_mode
        self.llm_model = llm_model
        self.llm_timeout_seconds = llm_timeout_seconds
        self.llm_fail_on_error = llm_fail_on_error
        self.firecrawl_api_key = firecrawl_api_key
        self.firecrawl_timeout_seconds = firecrawl_timeout_seconds
        self.skip_collection_guides = skip_collection_guides
        self.llm_connector = llm_connector or self._build_llm_connector()
        self.collector_factory = collector_factory or (
            lambda: PerplexityAPICollector(
                api_key=self.perplexity_api_key,
                max_results=self.perplexity_max_results,
                timeout_seconds=self.perplexity_timeout_seconds,
            )
        )
        self.openalex_collector_factory = openalex_collector_factory
        self.firecrawl_collector_factory = firecrawl_collector_factory

    _PROCESSING_FILENAMES = [
        "01-filtered-sources.json",
        "02-enriched-datasets.json",
        "03-ranked-datasets.json",
    ]

    def execute(self) -> dict[str, Any]:
        research_id = f"perplexity-intel-{uuid4().hex[:8]}"
        generated_at = datetime.now(timezone.utc).isoformat()
        run_dir = Path("data") / "runs" / research_id
        for subdir in ("config", "collection", "processing", "reports"):
            ensure_dir(run_dir / subdir)

        master_context = self._build_master_context()
        research_tracks = self._build_research_tracks()
        search_plan = self._build_search_plan(master_context, research_tracks)
        write_json(run_dir / "config" / "context.json", master_context.model_dump(mode="json"))
        write_json(run_dir / "config" / "tracks.json", [item.model_dump(mode="json") for item in research_tracks])
        write_json(run_dir / "master-context.json", master_context.model_dump(mode="json"))
        write_json(run_dir / "search-plan.json", [item.model_dump(mode="json") for item in search_plan])

        sessions = []
        if self.perplexity_enabled:
            collector = self.collector_factory()
            sessions.extend(collector.collect(search_plan))

        openalex_sessions = []
        openalex_raw_works = []
        if self.openalex_mode != "off":
            openalex_plan = self._select_openalex_plan(search_plan)
            openalex_collector = self._build_openalex_collector()
            openalex_sessions = openalex_collector.collect(openalex_plan)
            openalex_raw_works = [
                item.model_dump(mode="json") if hasattr(item, "model_dump") else item
                for item in getattr(openalex_collector, "raw_works", [])
            ]
            sessions.extend(openalex_sessions)
            write_json(run_dir / "collection" / "raw-openalex-works.json", openalex_raw_works)
        write_json(run_dir / "collection" / "raw-sessions.json", [item.model_dump(mode="json") for item in sessions])

        settings = PipelineSettings(query=self.base_query, limit=self.limit)
        context: dict[str, Any] = {
            "base_query": self.base_query,
            "settings": settings,
            "perplexity_master_context": master_context,
            "perplexity_search_plan": search_plan,
            "perplexity_sessions": sessions,
        }

        agents = [
            FilterValidateAgent(),
            EnrichAgent(
                llm_connector=self.llm_connector,
                fail_on_error=self.llm_fail_on_error,
                firecrawl_api_key=self.firecrawl_api_key,
                firecrawl_timeout_seconds=self.firecrawl_timeout_seconds,
                firecrawl_collector=self._build_firecrawl_collector(),
                skip_collection_guides=self.skip_collection_guides,
            ),
            RankAccessAgent(limit=self.limit),
            ReportAgent(
                llm_connector=self.llm_connector,
                fail_on_error=self.llm_fail_on_error,
            ),
        ]

        for idx, agent in enumerate(agents):
            updates = agent.run(context)
            context.update(updates)
            if idx < len(self._PROCESSING_FILENAMES):
                write_json(run_dir / "processing" / self._PROCESSING_FILENAMES[idx], self._serialize_updates(updates))

        report_path = run_dir / "reports" / f"{research_id}.md"
        write_markdown(report_path, context["intelligence_markdown"])

        html_report_path = run_dir / "reports" / "relatorio_100k.html"
        html_content = generate_html_report(
            datasets=context.get("ranked_datasets", []),
            master_context=master_context,
            search_plan=search_plan,
            metadata={
                "timestamp": generated_at,
                "total_tracks": len(search_plan),
                "pipeline_version": "2.0",
            },
        )
        html_report_path.write_text(html_content, encoding="utf-8")

        sources_csv_path = run_dir / "reports" / "sources.csv"
        write_catalog_csv(
            sources_csv_path,
            [
                {
                    "rank": item.rank,
                    "url": item.url,
                    "title": item.title,
                    "source_domain": item.source_domain,
                    "track_origin": item.track_origin,
                    "track_priority": item.track_priority,
                    "track_intent": item.track_intent,
                    "hierarchy_level": item.hierarchy_level,
                    "thematic_axis": item.thematic_axis,
                    "source_category": item.source_category,
                    "dataset_name": item.dataset_name,
                    "data_format": item.data_format,
                    "access_type": item.access_type,
                    "access_notes": item.access_notes,
                    "temporal_coverage": item.temporal_coverage or "",
                    "spatial_coverage": item.spatial_coverage or "",
                    "key_parameters": "|".join(item.key_parameters),
                    "needs_review": item.needs_review,
                    "enrichment_method": item.enrichment_method,
                    "collection_guide_available": item.collection_guide is not None,
                    "collection_effort": item.collection_guide.estimated_effort if item.collection_guide else "",
                    "collection_requires_login": item.collection_guide.requires_login if item.collection_guide else "",
                    "collection_direct_downloads": "|".join(item.collection_guide.direct_download_urls)
                    if item.collection_guide
                    else "",
                }
                for item in context.get("ranked_datasets", [])
            ],
            fieldnames=[
                "rank", "url", "title", "source_domain",
                "track_origin", "track_priority", "track_intent",
                "hierarchy_level", "thematic_axis", "source_category",
                "dataset_name", "data_format", "access_type", "access_notes",
                "temporal_coverage", "spatial_coverage", "key_parameters",
                "needs_review", "enrichment_method",
                "collection_guide_available", "collection_effort",
                "collection_requires_login", "collection_direct_downloads",
            ],
        )

        datasets_csv_path = run_dir / "reports" / "datasets.csv"
        write_catalog_csv(
            datasets_csv_path,
            [
                {
                    "rank": item.rank,
                    "dataset_name": item.dataset_name,
                    "title": item.title,
                    "url": item.url,
                    "source_domain": item.source_domain,
                    "track_origin": item.track_origin,
                    "track_priority": item.track_priority,
                    "hierarchy_level": item.hierarchy_level,
                    "thematic_axis": item.thematic_axis,
                    "source_category": item.source_category,
                    "data_format": item.data_format,
                    "access_type": item.access_type,
                    "access_notes": item.access_notes,
                    "temporal_coverage": item.temporal_coverage or "",
                    "spatial_coverage": item.spatial_coverage or "",
                    "key_parameters": "|".join(item.key_parameters),
                    "collection_guide_available": item.collection_guide is not None,
                    "collection_effort": item.collection_guide.estimated_effort if item.collection_guide else "",
                    "collection_requires_login": item.collection_guide.requires_login if item.collection_guide else "",
                    "collection_direct_downloads": "|".join(item.collection_guide.direct_download_urls)
                    if item.collection_guide
                    else "",
                }
                for item in context.get("ranked_datasets", [])
                if item.source_category in {"official_portal", "dataset"}
            ],
            fieldnames=[
                "rank", "dataset_name", "title", "url", "source_domain",
                "track_origin", "track_priority", "hierarchy_level", "thematic_axis",
                "source_category", "data_format", "access_type", "access_notes",
                "temporal_coverage", "spatial_coverage", "key_parameters",
                "collection_guide_available", "collection_effort",
                "collection_requires_login", "collection_direct_downloads",
            ],
        )

        intelligence_path = run_dir / "manifest.json"
        filtered_sources = context.get("filtered_sources", [])
        enriched_datasets = context.get("enriched_datasets", [])
        ranked_datasets = context.get("ranked_datasets", [])
        manifest = {
            "research_id": research_id,
            "generated_at": generated_at,
            "base_query": self.base_query,
            "master_context_path": str(run_dir / "master-context.json"),
            "perplexity_max_results": self.perplexity_max_results,
            "perplexity_enabled": self.perplexity_enabled,
            "openalex_mode": self.openalex_mode,
            "openalex_max_results": self.openalex_max_results,
            "openalex_session_count": len(openalex_sessions),
            "openalex_work_count": len(openalex_raw_works),
            "llm_mode": self.llm_mode,
            "llm_provider": self.llm_connector.provider if self.llm_connector else None,
            "llm_model": self.llm_connector.model if self.llm_connector else None,
            "collection_guides_enabled": bool(self.firecrawl_api_key) and not self.skip_collection_guides,
            "search_plan_count": len(search_plan),
            "session_count": len(sessions),
            "filtered_source_count": len(filtered_sources),
            "enriched_dataset_count": len(enriched_datasets),
            "ranked_dataset_count": len(ranked_datasets),
            "collection_guide_count": sum(1 for item in ranked_datasets if item.collection_guide is not None),
            "report_path": str(report_path),
            "html_report_path": str(html_report_path),
            "sources_csv_path": str(sources_csv_path),
            "datasets_csv_path": str(datasets_csv_path),
            "filter_meta": context.get("filter_meta", {}),
            "enrich_meta": context.get("enrich_meta", {}),
            "rank_meta": context.get("rank_meta", {}),
            "intelligence": context.get("intelligence_payload", {}),
        }
        write_json(intelligence_path, manifest)

        return {
            "research_id": research_id,
            "master_context_path": str(run_dir / "master-context.json"),
            "report_path": str(report_path),
            "html_report_path": str(html_report_path),
            "sources_csv_path": str(sources_csv_path),
            "datasets_csv_path": str(datasets_csv_path),
            "intelligence_path": str(intelligence_path),
            "filtered_source_count": len(filtered_sources),
            "enriched_dataset_count": len(enriched_datasets),
            "ranked_dataset_count": len(ranked_datasets),
            "collection_guide_count": sum(1 for item in ranked_datasets if item.collection_guide is not None),
        }

    def _build_master_context(self) -> PerplexityResearchContextRecord:
        if self.master_context_payload:
            return PerplexityResearchContextRecord.model_validate(self.master_context_payload)

        return PerplexityResearchContextRecord(
            context_id="ctx-article-001",
            article_goal=f"Discover sources, datasets and academic knowledge for the research topic: {self.base_query}",
            geographic_scope=[],
            thematic_axes=[
                "environmental context",
                "anthropic pressures and drivers",
                "monitoring and time series",
                "environmental response indicators",
                "scientific and institutional data sources",
            ],
            preferred_sources=[
                "official and institutional portals",
                "academic repositories",
                "technical reports with citations to data",
                "catalogs, APIs and time-series datasets",
            ],
            expected_outputs=[
                "direct links to portals, documents or repositories",
                "datasets and recurring monitoring programs",
                "academic studies that cite data sources",
                "methodological clues for the article",
            ],
            exclusions=[
                "generic summaries without sources",
                "promotional content",
                "low-value contextual noise",
            ],
            notes=[
                f"User-provided research context: {self.base_query}",
                "Prefer a few deep thematic chats over one broad generic search.",
            ],
        )

    def _build_research_tracks(self) -> list[PerplexityResearchTrackRecord]:
        payload = self.research_tracks_payload or list(self.DEFAULT_RESEARCH_TRACKS)
        tracks = [PerplexityResearchTrackRecord.model_validate(item) for item in payload]
        if self.research_tracks_payload:
            return tracks
        return tracks[: self.max_searches]

    def _build_search_plan(
        self,
        master_context: PerplexityResearchContextRecord,
        research_tracks: list[PerplexityResearchTrackRecord],
    ) -> list[PerplexitySearchQueryRecord]:
        plan: list[PerplexitySearchQueryRecord] = []
        for index, track in enumerate(research_tracks, start=1):
            query_text = self._compose_chat_prompt(master_context=master_context, track=track)
            plan.append(
                PerplexitySearchQueryRecord(
                    query_id=f"pplx-q-{index:02d}",
                    base_query=self.base_query,
                    query_text=query_text,
                    search_profile=track.search_profile,
                    target_intent=track.target_intent,
                    research_track=track.research_track,
                    chat_label=track.chat_label,
                    research_question=track.research_question,
                    task_prompt=track.task_prompt,
                    priority=track.priority,
                )
            )
        return plan

    @staticmethod
    def _compose_chat_prompt(
        *,
        master_context: PerplexityResearchContextRecord,
        track: PerplexityResearchTrackRecord,
    ) -> str:
        """Compõe query focada para a Perplexity Search API.

        Usa pergunta específica da trilha + hint de portais/fontes do task_prompt
        + âncora geográfica. Evita contexto acadêmico genérico que iguala queries
        entre trilhas e faz a Search API retornar apenas artigos sobre o tema.
        """
        parts: list[str] = []

        # 1. Pergunta da trilha — âncora temática específica por trilha
        question = PerplexityIntelligencePipeline._compact_text(track.research_question, 420)
        if question:
            parts.append(f"Pergunta principal: {question}")

        # 2. Primeiros ~120 chars do task_prompt — contém nomes de portais e fontes concretas
        task_hint = PerplexityIntelligencePipeline._compact_text(track.task_prompt, 720)
        if task_hint:
            parts.append(f"Tarefa especifica: {task_hint}")

        # 3. Primeiro item do escopo geográfico como âncora de localização
        if master_context.geographic_scope:
            geo = PerplexityIntelligencePipeline._compact_list(master_context.geographic_scope, 2, 260)
            if geo:
                parts.append(f"Recorte geografico: {geo}")

        preferred_sources = PerplexityIntelligencePipeline._compact_list(master_context.preferred_sources, 6, 320)
        if preferred_sources:
            parts.append(
                "Priorize paginas primarias de dataset, catalogo, API ou download direto em fontes como: "
                f"{preferred_sources}."
            )

        expected_outputs = PerplexityIntelligencePipeline._compact_list(master_context.expected_outputs, 3, 220)
        if expected_outputs:
            parts.append(f"Busque preferencialmente: {expected_outputs}.")

        exclusions = PerplexityIntelligencePipeline._compact_list(master_context.exclusions, 3, 220)
        if exclusions:
            parts.append(f"Evite: {exclusions}.")

        parts.append(
            "Nao priorize blogs, tutoriais, rankings de sites, curadorias ou paginas agregadoras quando houver "
            "fonte oficial, institucional ou academica equivalente."
        )
        parts.append(
            "Retorne preferencialmente paginas que exponham metadados, filtros reais, codigos internos, API, "
            "ou links diretos de download."
        )

        return ". ".join(parts)

    @staticmethod
    def _compact_text(value: str, limit: int) -> str:
        cleaned = " ".join(str(value or "").split())
        if len(cleaned) <= limit:
            return cleaned
        return cleaned[: max(limit - 3, 0)].rstrip() + "..."

    @staticmethod
    def _compact_list(values: list[str], max_items: int, limit: int) -> str:
        items = [" ".join(str(value or "").split()) for value in values if str(value or "").strip()]
        if not items:
            return ""
        joined = "; ".join(items[:max_items])
        return PerplexityIntelligencePipeline._compact_text(joined, limit)

    def _build_llm_connector(self) -> LLMConnector | None:
        if self.llm_mode == "off":
            return None

        api_key = os.getenv("OPENAI_API_KEY", "").strip()
        if not api_key:
            if self.llm_mode == "openai":
                raise LLMConnectorError("OPENAI_API_KEY ausente para inferencia obrigatoria.")
            return None

        try:
            return OpenAIResponsesConnector(
                api_key=api_key,
                model=self.llm_model,
                timeout_seconds=self.llm_timeout_seconds,
            )
        except Exception:
            if self.llm_fail_on_error or self.llm_mode == "openai":
                raise
            return None

    def _build_firecrawl_collector(self) -> FirecrawlCollector | None:
        if self.skip_collection_guides or not self.firecrawl_api_key:
            return None
        if self.firecrawl_collector_factory is not None:
            return self.firecrawl_collector_factory()
        try:
            return FirecrawlCollector(
                api_key=self.firecrawl_api_key,
                timeout_seconds=self.firecrawl_timeout_seconds,
            )
        except Exception:
            return None

    def _build_openalex_collector(self) -> OpenAlexAPICollector:
        if self.openalex_collector_factory is not None:
            return self.openalex_collector_factory()
        return OpenAlexAPICollector(
            max_results=self.openalex_max_results,
            timeout_seconds=self.openalex_timeout_seconds,
            api_key=self.openalex_api_key,
            mailto=self.openalex_mailto,
            from_publication_year=self.openalex_from_publication_year,
            to_publication_year=self.openalex_to_publication_year,
        )

    def _select_openalex_plan(
        self,
        search_plan: list[PerplexitySearchQueryRecord],
    ) -> list[PerplexitySearchQueryRecord]:
        if self.openalex_mode == "all":
            return search_plan
        if self.openalex_mode == "academic":
            selected: list[PerplexitySearchQueryRecord] = []
            for query in search_plan:
                haystack = " ".join(
                    [
                        query.search_profile,
                        query.target_intent,
                        query.research_track,
                        query.research_question,
                        query.task_prompt,
                    ]
                ).lower()
                if any(token in haystack for token in ("academic", "academica", "literatura", "artigo", "tese")):
                    selected.append(query)
            return selected
        return []

    @staticmethod
    def _serialize_updates(updates: dict[str, Any]) -> dict[str, Any]:
        serialized: dict[str, Any] = {}
        for key, value in updates.items():
            if hasattr(value, "model_dump"):
                serialized[key] = value.model_dump(mode="json")
            elif isinstance(value, list):
                serialized[key] = [
                    item.model_dump(mode="json") if hasattr(item, "model_dump") else item
                    for item in value
                ]
            else:
                serialized[key] = value
        return serialized
