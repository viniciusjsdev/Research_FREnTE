"""Coleta academica via API OpenAlex."""

from __future__ import annotations

from urllib.parse import urlparse

import httpx

from src.schemas.records import (
    OpenAlexWorkRecord,
    PerplexityLinkRecord,
    PerplexitySearchQueryRecord,
    PerplexitySearchSessionRecord,
)

OPENALEX_WORKS_URL = "https://api.openalex.org/works"


class OpenAlexAPIError(RuntimeError):
    """Erro operacional ao chamar a API da OpenAlex."""


class OpenAlexAPICollector:
    """Executa buscas academicas estruturadas na API OpenAlex."""

    def __init__(
        self,
        *,
        max_results: int = 25,
        timeout_seconds: float = 60.0,
        api_key: str = "",
        mailto: str = "",
        from_publication_year: int | None = None,
        to_publication_year: int | None = None,
    ) -> None:
        self.max_results = max(1, min(max_results, 100))
        self.timeout_seconds = timeout_seconds
        self.api_key = api_key
        self.mailto = mailto
        self.from_publication_year = from_publication_year
        self.to_publication_year = to_publication_year
        self.raw_works: list[OpenAlexWorkRecord] = []

    def collect(self, query_plan: list[PerplexitySearchQueryRecord]) -> list[PerplexitySearchSessionRecord]:
        if not query_plan:
            return []

        self.raw_works = []
        sessions: list[PerplexitySearchSessionRecord] = []
        for query in query_plan:
            search_texts = self._search_texts(query)
            used_searches: list[str] = []
            try:
                seen_ids: set[str] = set()
                works: list[OpenAlexWorkRecord] = []
                for search_text in search_texts:
                    used_searches.append(search_text)
                    results = self._call_api(search_text)
                    for item in results:
                        openalex_id = str(item.get("id") or "")
                        if openalex_id in seen_ids:
                            continue
                        seen_ids.add(openalex_id)
                        work = self._normalize_work(query.query_id, search_text, item)
                        if self._is_relevant_work(query, work):
                            works.append(work)
                    if len(works) >= self.max_results:
                        break
                works = works[: self.max_results]
                self.raw_works.extend(works)

                links = [
                    PerplexityLinkRecord(
                        title=work.title,
                        url=self._best_url(work),
                        domain=_extract_domain(self._best_url(work)),
                        snippet=self._snippet(work),
                    )
                    for work in works
                    if self._best_url(work).startswith("http")
                ]
                answer_text = "\n\n".join(self._answer_line(work) for work in works)
                sessions.append(
                    PerplexitySearchSessionRecord(
                        query_id=query.query_id,
                        query_text=" | ".join(used_searches),
                        search_profile=query.search_profile,
                        target_intent="academic_knowledge",
                        research_track=query.research_track,
                        chat_label=f"{query.chat_label}-openalex" if query.chat_label else "openalex",
                        research_question=query.research_question,
                        collection_status="ok",
                        collection_method="openalex_api",
                        request_endpoint=OPENALEX_WORKS_URL,
                        answer_text=answer_text,
                        visible_source_count=len(links),
                        links=links,
                        blockers=[],
                        notes=[
                            f"max_results:{self.max_results}",
                            f"searches:{len(used_searches)}",
                            "source:openalex_api",
                            "raw_payload:collection/raw-openalex-works.json",
                        ],
                    )
                )
            except Exception as exc:  # noqa: BLE001
                sessions.append(
                    PerplexitySearchSessionRecord(
                        query_id=query.query_id,
                        query_text=" | ".join(used_searches or search_texts),
                        search_profile=query.search_profile,
                        target_intent="academic_knowledge",
                        research_track=query.research_track,
                        chat_label=f"{query.chat_label}-openalex" if query.chat_label else "openalex",
                        research_question=query.research_question,
                        collection_status="error",
                        collection_method="openalex_api",
                        request_endpoint=OPENALEX_WORKS_URL,
                        answer_text="",
                        visible_source_count=0,
                        links=[],
                        blockers=[f"api_error:{type(exc).__name__}"],
                        notes=[str(exc)[:300]],
                    )
                )
        return sessions

    def _call_api(self, search_text: str) -> list[dict[str, object]]:
        params: dict[str, object] = {
            "search": search_text,
            "per_page": self.max_results,
            "sort": "relevance_score:desc",
            "select": ",".join(
                [
                    "id",
                    "doi",
                    "display_name",
                    "publication_year",
                    "publication_date",
                    "type",
                    "cited_by_count",
                    "is_retracted",
                    "primary_location",
                    "best_oa_location",
                    "open_access",
                    "authorships",
                    "keywords",
                    "concepts",
                    "abstract_inverted_index",
                ]
            ),
        }
        filters: list[str] = []
        if self.from_publication_year:
            filters.append(f"from_publication_date:{self.from_publication_year}-01-01")
        if self.to_publication_year:
            filters.append(f"to_publication_date:{self.to_publication_year}-12-31")
        if filters:
            params["filter"] = ",".join(filters)
        if self.api_key:
            params["api_key"] = self.api_key
        if self.mailto:
            params["mailto"] = self.mailto

        response = httpx.get(
            OPENALEX_WORKS_URL,
            params=params,
            headers={"User-Agent": self._user_agent()},
            timeout=self.timeout_seconds,
        )
        if response.status_code != 200:
            raise OpenAlexAPIError(f"HTTP {response.status_code}: {response.text[:300]}")
        data = response.json()
        results = data.get("results", [])
        return results if isinstance(results, list) else []

    def _user_agent(self) -> str:
        suffix = f" ({self.mailto})" if self.mailto else ""
        return f"Research-FREnTE OpenAlex collector{suffix}"

    @staticmethod
    def _search_text(query: PerplexitySearchQueryRecord) -> str:
        return OpenAlexAPICollector._search_texts(query)[0]

    @staticmethod
    def _search_texts(query: PerplexitySearchQueryRecord) -> list[str]:
        track = query.research_track.lower()
        track_queries = {
            "jupia_sucuriu": ["Jupia Sucuriu", "Jupia reservoir"],
            "geografia_bacia": ["Jupia reservoir Upper Parana basin", "Upper Parana basin Jupia"],
            "operacao_reservatorios": ["Jupia reservoir hydrology operation", "Upper Parana reservoirs operation"],
            "hidrologia_ana": ["Rio Parana Jupia hydrology", "Upper Parana river hydrology"],
            "qualidade_agua": ["Jupia reservoir water quality", "Upper Parana reservoir water quality"],
            "poluicao_saneamento": ["Upper Parana Tiete pollution sewage", "Tiete River pollution reservoir"],
            "sedimentos_turbidez": [
                "Jupia reservoir sediment",
                "Upper Parana sediment",
                "Tiete reservoir sediment turbidity",
            ],
            "uso_solo": ["Upper Parana basin land use agriculture", "Tiete basin land use agriculture"],
            "clima_chuva": ["Upper Parana basin drought rainfall", "La Plata basin drought Parana"],
            "literatura_contexto": ["Jupia reservoir Alto Parana", "Upper Parana River reservoirs"],
        }
        for key, value in track_queries.items():
            if key in track:
                return value

        parts = [
            query.base_query,
            query.research_question,
            query.task_prompt,
        ]
        text = " ".join(" ".join(str(part or "").split()) for part in parts if str(part or "").strip())
        return [text[:950]]

    @staticmethod
    def _is_relevant_work(query: PerplexitySearchQueryRecord, work: OpenAlexWorkRecord) -> bool:
        text = " ".join(
            [
                work.title,
                work.abstract,
                work.source_display_name,
                " ".join(work.keywords),
                " ".join(work.concepts),
            ]
        ).lower()
        geo_terms = (
            "jupia",
            "jupiá",
            "sucuriu",
            "parana",
            "paraná",
            "paranaiba",
            "paranaíba",
            "tiete",
            "tietê",
            "la plata",
            "alto parana",
            "upper parana",
            "barra bonita",
            "tres irmaos",
            "três irmãos",
        )
        water_terms = (
            "reservoir",
            "river",
            "basin",
            "hydrolog",
            "water",
            "sediment",
            "turbidity",
            "pollution",
            "sewage",
            "eutroph",
            "rainfall",
            "drought",
            "quality",
            "fish",
            "floodplain",
            "bacia",
            "rio",
            "reservatório",
            "reservatorio",
        )

        has_geo = any(term in text for term in geo_terms)
        has_water_context = any(term in text for term in water_terms)
        if not has_geo or not has_water_context:
            return False

        if "jupia_sucuriu" in query.research_track.lower():
            return any(term in text for term in ("jupia", "jupiá", "sucuriu"))
        return True

    @staticmethod
    def _normalize_work(query_id: str, search_text: str, item: dict[str, object]) -> OpenAlexWorkRecord:
        primary_location = _as_dict(item.get("primary_location"))
        best_oa_location = _as_dict(item.get("best_oa_location"))
        open_access = _as_dict(item.get("open_access"))
        source = _as_dict(primary_location.get("source") or best_oa_location.get("source"))
        authorships = item.get("authorships") if isinstance(item.get("authorships"), list) else []

        authors: list[str] = []
        institutions: list[str] = []
        countries: list[str] = []
        for authorship in authorships:
            row = _as_dict(authorship)
            author = _as_dict(row.get("author"))
            if author.get("display_name"):
                authors.append(str(author["display_name"]))
            raw_institutions = row.get("institutions")
            for institution in raw_institutions if isinstance(raw_institutions, list) else []:
                inst = _as_dict(institution)
                if inst.get("display_name"):
                    institutions.append(str(inst["display_name"]))
                if inst.get("country_code"):
                    countries.append(str(inst["country_code"]))

        raw_keywords = item.get("keywords")
        raw_keywords = raw_keywords if isinstance(raw_keywords, list) else []
        keywords = [
            str(_as_dict(keyword).get("display_name") or _as_dict(keyword).get("keyword") or "")
            for keyword in raw_keywords
        ]
        raw_concepts = item.get("concepts")
        raw_concepts = raw_concepts if isinstance(raw_concepts, list) else []
        concepts = [
            str(_as_dict(concept).get("display_name") or "")
            for concept in raw_concepts
        ]

        openalex_id = str(item.get("id") or "")
        return OpenAlexWorkRecord(
            query_id=query_id,
            search_text=search_text,
            openalex_id=openalex_id,
            openalex_url=openalex_id,
            doi=str(item.get("doi") or ""),
            title=str(item.get("display_name") or ""),
            publication_year=_int_or_none(item.get("publication_year")),
            publication_date=str(item.get("publication_date") or "") or None,
            work_type=str(item.get("type") or ""),
            cited_by_count=int(item.get("cited_by_count") or 0),
            is_open_access=bool(open_access.get("is_oa") or primary_location.get("is_oa") or best_oa_location.get("is_oa")),
            landing_page_url=str(primary_location.get("landing_page_url") or best_oa_location.get("landing_page_url") or ""),
            pdf_url=str(best_oa_location.get("pdf_url") or primary_location.get("pdf_url") or ""),
            oa_url=str(open_access.get("oa_url") or ""),
            source_display_name=str(source.get("display_name") or ""),
            authors=_dedupe(authors)[:12],
            institutions=_dedupe(institutions)[:12],
            countries=_dedupe(countries)[:8],
            keywords=[item for item in _dedupe(keywords) if item][:12],
            concepts=[item for item in _dedupe(concepts) if item][:12],
            abstract=_abstract_from_index(item.get("abstract_inverted_index")),
            raw=item,
        )

    @staticmethod
    def _best_url(work: OpenAlexWorkRecord) -> str:
        return work.pdf_url or work.oa_url or work.doi or work.landing_page_url or work.openalex_url

    @staticmethod
    def _snippet(work: OpenAlexWorkRecord) -> str:
        parts = [
            "OpenAlex",
            str(work.publication_year or ""),
            work.work_type,
            f"{work.cited_by_count} citacoes",
            f"fonte: {work.source_display_name}" if work.source_display_name else "",
            f"DOI: {work.doi}" if work.doi else "",
            f"PDF: {work.pdf_url}" if work.pdf_url else "",
            work.abstract[:260],
        ]
        return " | ".join(part for part in parts if part)

    @staticmethod
    def _answer_line(work: OpenAlexWorkRecord) -> str:
        authors = ", ".join(work.authors[:3])
        source = f" {work.source_display_name}." if work.source_display_name else ""
        pdf = f" PDF: {work.pdf_url}." if work.pdf_url else ""
        return (
            f"{work.title} ({work.publication_year or 's.d.'}). "
            f"{authors}.{source} Cited by: {work.cited_by_count}. "
            f"DOI: {work.doi or 'n/a'}.{pdf}"
        )


def _as_dict(value: object) -> dict[str, object]:
    return value if isinstance(value, dict) else {}


def _int_or_none(value: object) -> int | None:
    try:
        return int(value) if value is not None else None
    except (TypeError, ValueError):
        return None


def _dedupe(values: list[str]) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for value in values:
        cleaned = " ".join(str(value or "").split())
        key = cleaned.lower()
        if cleaned and key not in seen:
            seen.add(key)
            out.append(cleaned)
    return out


def _abstract_from_index(value: object) -> str:
    index = value if isinstance(value, dict) else {}
    positions: list[tuple[int, str]] = []
    for word, raw_positions in index.items():
        if not isinstance(raw_positions, list):
            continue
        for position in raw_positions:
            try:
                positions.append((int(position), str(word)))
            except (TypeError, ValueError):
                continue
    return " ".join(word for _, word in sorted(positions))


def _extract_domain(url: str) -> str:
    try:
        return (urlparse(url).hostname or "").replace("www.", "")
    except Exception:
        return ""


__all__ = ["OpenAlexAPICollector", "OpenAlexAPIError", "OPENALEX_WORKS_URL"]
