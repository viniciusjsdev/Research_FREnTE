from unittest.mock import MagicMock, patch

from src.connectors.openalex_api import OpenAlexAPICollector, OpenAlexAPIError
from src.schemas.records import PerplexitySearchQueryRecord


def _make_query(query_id: str = "pplx-q-01") -> PerplexitySearchQueryRecord:
    return PerplexitySearchQueryRecord(
        query_id=query_id,
        base_query="Jupia poluicao qualidade agua sedimentos",
        query_text="Quais artigos academicos existem sobre Jupia?",
        search_profile="academic_knowledge",
        target_intent="academic_knowledge",
        research_track="n4_literatura_contexto_integrado_jupia",
        chat_label="chat-literatura",
        research_question="Quais artigos ajudam a interpretar Jupia?",
        task_prompt="Busque artigos, teses e relatorios com dados primarios.",
        priority="medium",
    )


def test_collect_returns_empty_for_empty_plan() -> None:
    collector = OpenAlexAPICollector()
    assert collector.collect([]) == []


def test_collect_ok_session_and_preserves_raw_work() -> None:
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "results": [
            {
                "id": "https://openalex.org/W123",
                "doi": "https://doi.org/10.123/example",
                "display_name": "Water quality in Jupia Reservoir",
                "publication_year": 2019,
                "publication_date": "2019-01-01",
                "type": "article",
                "cited_by_count": 7,
                "primary_location": {
                    "landing_page_url": "https://example.org/article",
                    "pdf_url": "https://example.org/article.pdf",
                    "source": {"display_name": "Example Journal"},
                },
                "best_oa_location": {},
                "open_access": {"is_oa": True, "oa_url": "https://example.org/article"},
                "authorships": [
                    {
                        "author": {"display_name": "Ana Silva"},
                        "institutions": [{"display_name": "UNESP", "country_code": "BR"}],
                    }
                ],
                "keywords": [{"display_name": "water quality"}],
                "concepts": [{"display_name": "Reservoir"}],
                "abstract_inverted_index": {"Jupia": [0], "Reservoir": [1]},
            }
        ]
    }

    collector = OpenAlexAPICollector(max_results=5)
    with patch("src.connectors.openalex_api.httpx.get", return_value=mock_response):
        sessions = collector.collect([_make_query()])

    assert len(sessions) == 1
    session = sessions[0]
    assert session.collection_status == "ok"
    assert session.collection_method == "openalex_api"
    assert session.query_id == "pplx-q-01"
    assert len(session.links) == 1
    assert session.links[0].url == "https://example.org/article.pdf"
    assert "OpenAlex" in session.links[0].snippet
    assert len(collector.raw_works) == 1
    assert collector.raw_works[0].doi == "https://doi.org/10.123/example"
    assert collector.raw_works[0].abstract == "Jupia Reservoir"


def test_collect_error_session_on_api_failure() -> None:
    mock_response = MagicMock()
    mock_response.status_code = 429
    mock_response.text = "Too Many Requests"

    collector = OpenAlexAPICollector()
    with patch("src.connectors.openalex_api.httpx.get", return_value=mock_response):
        sessions = collector.collect([_make_query()])

    assert len(sessions) == 1
    assert sessions[0].collection_status == "error"
    assert any("api_error" in blocker for blocker in sessions[0].blockers)


def test_openalex_api_error_is_runtime_error() -> None:
    assert isinstance(OpenAlexAPIError("teste"), RuntimeError)
