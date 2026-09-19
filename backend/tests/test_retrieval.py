"""Retrieval service tests: TF-IDF behavior over the real knowledge files."""
from pathlib import Path

from app.services.retrieval_service import RetrievalService


def test_refund_query_retrieves_policies() -> None:
    """Given the knowledge base
    When a refund question is asked
    Then policies.md is the top result with a positive score."""
    service = RetrievalService()
    results = service.retrieve("What is your refund policy?", top_k=3)
    assert results
    assert results[0].document == "policies.md"
    assert results[0].score > 0
    assert "14-day" in results[0].chunk


def test_pricing_query_retrieves_faq() -> None:
    """Given the knowledge base
    When a pricing question is asked
    Then faq.md appears in the results."""
    service = RetrievalService()
    results = service.retrieve("How much does the starter plan cost?", top_k=3)
    assert results
    assert any(result.document == "faq.md" for result in results)


def test_gibberish_query_returns_nothing() -> None:
    """Given the knowledge base
    When the query shares no tokens with any document
    Then an empty list is returned (no fake matches)."""
    service = RetrievalService()
    assert service.retrieve("xyzzy plover wombat", top_k=3) == []


def test_missing_knowledge_dir_returns_empty() -> None:
    """Given a nonexistent knowledge directory
    When retrieve is called
    Then a clean empty result is returned (spec: degraded, not crashed)."""
    service = RetrievalService(Path("definitely/not/a/real/dir"))
    assert service.retrieve("refund", top_k=3) == []


def test_knowledge_base_is_chunked() -> None:
    """Given the knowledge base
    When it is indexed
    Then the markdown is split into multiple heading-level chunks."""
    service = RetrievalService()
    service._load()
    assert len(service._chunks) >= 10


def test_top_k_limits_results() -> None:
    """Given the knowledge base
    When top_k=2 is requested
    Then at most 2 results come back."""
    service = RetrievalService()
    results = service.retrieve("whatsapp automation support", top_k=2)
    assert len(results) <= 2
