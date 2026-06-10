"""Schemas principais do fluxo Perplexity-first."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Literal

from pydantic import BaseModel, Field

# ---------------------------------------------------------------------------
# Mapeamentos de herança de trilha — usados pelo EnrichAgent (sem LLM)
# ---------------------------------------------------------------------------

TRACK_TO_LEVEL: dict[str, str] = {
    "n1_": "macro",
    "n2_": "meso",
    "n3_": "bridge",
    "n4_": "micro",
}

TRACK_TO_AXIS: dict[str, str] = {
    "n1_bacia_geomorfologia": "delimitação e geomorfologia",
    "n1_uso_cobertura_solo": "uso e cobertura do solo",
    "n1_clima_hidrologia": "clima e hidrologia",
    "n2_saneamento_esgoto": "saneamento e esgoto",
    "n2_desmatamento_queimadas": "desmatamento e queimadas",
    "n2_agro_residuos_ocupacao": "agropecuária, resíduos e ocupação",
    "n3_qualidade_agua_reservatorios": "qualidade da água nos reservatórios",
    "n3_operacao_reservatorios": "operação dos reservatórios",
    "n3_batimetria_morfometria": "batimetria e morfometria",
    "n4_materia_organica_cdom": "matéria orgânica e CDOM",
    "n4_sensoriamento_remoto_agua": "sensoriamento remoto da qualidade da água",
    "n4_series_temporais_tendencias": "séries temporais e tendências",
}

INTENT_TO_CATEGORY: dict[str, str] = {
    "dataset_discovery": "dataset",
    "academic_knowledge": "academic",
    "contextual_intelligence": "contextual",
}

DOMAIN_CATEGORY_OVERRIDES: dict[str, str] = {
    "cetesb.sp.gov.br": "official_portal",
    "qualar.cetesb.sp.gov.br": "official_portal",
    "snirh.gov.br": "official_portal",
    "hidroweb.ana.gov.br": "official_portal",
    "ana.gov.br": "official_portal",
    "ibge.gov.br": "official_portal",
    "sidra.ibge.gov.br": "official_portal",
    "ons.org.br": "official_portal",
    "inpe.br": "official_portal",
    "terrabrasilis.dpi.inpe.br": "official_portal",
    "mapbiomas.org": "official_portal",
    "scielo.br": "academic",
    "doi.org": "academic",
}


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class PerplexityResearchTrackRecord(BaseModel):
    """Configuracao de uma frente tematica de busca no Perplexity."""

    research_track: str
    chat_label: str
    search_profile: str = "general_environmental_search"
    target_intent: str = "dataset_discovery"
    research_question: str
    task_prompt: str
    priority: str = "medium"


class PerplexitySearchQueryRecord(BaseModel):
    """Consulta planejada para coleta via Perplexity."""

    query_id: str
    base_query: str
    query_text: str
    search_profile: str
    target_intent: str
    research_track: str = ""
    chat_label: str = ""
    research_question: str = ""
    task_prompt: str = ""
    priority: str = "medium"


class PerplexityResearchContextRecord(BaseModel):
    """Contexto mestre da pesquisa."""

    context_id: str
    article_goal: str
    geographic_scope: list[str] = Field(default_factory=list)
    thematic_axes: list[str] = Field(default_factory=list)
    preferred_sources: list[str] = Field(default_factory=list)
    expected_outputs: list[str] = Field(default_factory=list)
    exclusions: list[str] = Field(default_factory=list)
    notes: list[str] = Field(default_factory=list)


class PerplexityLinkRecord(BaseModel):
    """Link visivel coletado em uma resposta do Perplexity."""

    title: str = ""
    url: str
    domain: str = ""
    snippet: str = ""


class PerplexitySearchSessionRecord(BaseModel):
    """Resposta bruta coletada via Perplexity Search API."""

    query_id: str
    query_text: str
    search_profile: str
    target_intent: str
    research_track: str = ""
    chat_label: str = ""
    research_question: str = ""
    collection_status: str = "ok"
    collection_method: str = "search_api"
    request_endpoint: str = ""
    answer_text: str = ""
    visible_source_count: int = 0
    links: list[PerplexityLinkRecord] = Field(default_factory=list)
    blockers: list[str] = Field(default_factory=list)
    notes: list[str] = Field(default_factory=list)
    collected_at: datetime = Field(default_factory=_utcnow)


class OpenAlexWorkRecord(BaseModel):
    """Registro academico estruturado preservado a partir da API OpenAlex."""

    query_id: str
    search_text: str
    openalex_id: str = ""
    openalex_url: str = ""
    doi: str = ""
    title: str = ""
    publication_year: int | None = None
    publication_date: str | None = None
    work_type: str = ""
    cited_by_count: int = 0
    is_open_access: bool = False
    landing_page_url: str = ""
    pdf_url: str = ""
    oa_url: str = ""
    source_display_name: str = ""
    authors: list[str] = Field(default_factory=list)
    institutions: list[str] = Field(default_factory=list)
    countries: list[str] = Field(default_factory=list)
    keywords: list[str] = Field(default_factory=list)
    concepts: list[str] = Field(default_factory=list)
    abstract: str = ""
    raw: dict[str, Any] = Field(default_factory=dict)
    collected_at: datetime = Field(default_factory=_utcnow)


# ---------------------------------------------------------------------------
# Schemas do pipeline refatorado (4 etapas)
# ---------------------------------------------------------------------------


class CollectionGuide(BaseModel):
    """Guia de coleta extraído automaticamente de um portal via Firecrawl."""

    steps: list[str] = Field(
        default_factory=list,
        description="Passos numerados para coletar os dados no portal.",
    )
    filters_available: dict[str, str] = Field(
        default_factory=dict,
        description="Filtros identificados. Chave: nome. Valor: opções relevantes para o Tietê.",
    )
    download_format: str = Field(
        default="unknown",
        description="Formato do arquivo de download. Ex: 'CSV separador ;', 'Shapefile ZIP'.",
    )
    estimated_effort: Literal["minutes", "hours", "days", "requires_contact"] = Field(
        default="hours",
        description="Esforço estimado para coletar.",
    )
    caveats: list[str] = Field(
        default_factory=list,
        description="Alertas e limitações do portal.",
    )
    requires_login: bool = Field(
        default=False,
        description="Se o portal exige cadastro ou login.",
    )
    direct_download_urls: list[str] = Field(
        default_factory=list,
        description="URLs diretas de arquivos encontrados na página.",
    )


class FilteredSource(BaseModel):
    """Fonte filtrada e validada heuristicamente a partir da coleta bruta."""

    url: str
    title: str
    snippet: str
    source_domain: str

    # herdado do track que gerou este resultado
    track_origin: str
    track_priority: str
    track_intent: str

    needs_review: bool = False
    filter_notes: list[str] = Field(default_factory=list)


class EnrichedDataset(FilteredSource):
    """Fonte enriquecida com metadados herdados do track e extraídos pela LLM."""

    # Fase A — herdado do track (determinístico)
    hierarchy_level: Literal["macro", "meso", "bridge", "micro"] = "macro"
    thematic_axis: str = ""
    source_category: str = "contextual"  # official_portal | academic | dataset | contextual

    # Fase B — extraído pela LLM (ou heurística de fallback)
    dataset_name: str = ""
    dataset_description: str = ""
    data_format: Literal[
        "structured",
        "semi_structured",
        "pdf_report",
        "academic_paper",
        "geospatial_platform",
        "unknown",
    ] = "unknown"
    temporal_coverage: str | None = None
    spatial_coverage: str | None = None
    key_parameters: list[str] = Field(default_factory=list)
    collection_guide: CollectionGuide | None = None

    enrichment_method: Literal["llm", "heuristic"] = "heuristic"
    llm_model: str | None = None


class RankedDataset(EnrichedDataset):
    """Dataset enriquecido com rank de acesso e tipo de acesso classificado."""

    rank: int = 0
    access_type: Literal[
        "direct_download",
        "api_access",
        "web_portal",
        "geospatial_platform",
        "pdf_extraction",
        "restricted",
        "unknown",
    ] = "unknown"
    access_notes: str = ""


class CollectionArtifactRecord(BaseModel):
    """Arquivo ou resposta persistida durante uma coleta operacional."""

    artifact_id: str
    target_id: str
    source_name: str
    status: str = "collected"
    relative_path: str
    download_url: str = ""
    media_type: str = ""
    file_format: str = ""
    content_length: int | None = None
    checksum_sha256: str = ""
    notes: list[str] = Field(default_factory=list)
    collected_at: datetime = Field(default_factory=_utcnow)


class OperationalCollectionTargetRecord(BaseModel):
    """Resumo auditavel da coleta de uma fonte operacional."""

    target_id: str
    source_name: str
    dataset_name: str
    collection_status: Literal["collected", "partial", "blocked", "error", "not_attempted"] = "not_attempted"
    access_type: str = "unknown"
    collection_method: str = "http_download"
    requires_auth: bool = False
    year_start: int | None = None
    year_end: int | None = None
    bbox: str | None = None
    provenance_urls: list[str] = Field(default_factory=list)
    blockers: list[str] = Field(default_factory=list)
    notes: list[str] = Field(default_factory=list)
    join_keys: list[str] = Field(default_factory=list)
    staging_outputs: list[str] = Field(default_factory=list)
    analytic_outputs: list[str] = Field(default_factory=list)
    raw_artifacts: list[CollectionArtifactRecord] = Field(default_factory=list)


class OperationalCollectionRunRecord(BaseModel):
    """Manifesto consolidado de uma rodada de coleta operacional."""

    run_id: str
    pipeline_name: str = "operational_dataset_collection"
    generated_at: datetime = Field(default_factory=_utcnow)
    target_ids: list[str] = Field(default_factory=list)
    target_count: int = 0
    collected_count: int = 0
    partial_count: int = 0
    blocked_count: int = 0
    error_count: int = 0
    targets: list[OperationalCollectionTargetRecord] = Field(default_factory=list)
