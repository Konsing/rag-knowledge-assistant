import pytest

from app.ingestion.arxiv_fetcher import _build_pdf_url, _extract_arxiv_id


@pytest.mark.parametrize(
    ("url", "expected"),
    [
        ("https://arxiv.org/abs/2301.00001", "2301.00001"),
        ("https://arxiv.org/pdf/2301.00001v2.pdf", "2301.00001v2"),
        ("https://arxiv.org/abs/hep-th/9901001", "hep-th/9901001"),
        ("https://export.arxiv.org/pdf/math.AG/0301234", "math.AG/0301234"),
    ],
)
def test_extract_arxiv_id(url, expected):
    assert _extract_arxiv_id(url) == expected


def test_rejects_lookalike_host():
    with pytest.raises(ValueError):
        _extract_arxiv_id("https://evil.example/arxiv.org/abs/2301.00001")


def test_legacy_pdf_url():
    assert _build_pdf_url("hep-th/9901001") == "https://arxiv.org/pdf/hep-th/9901001.pdf"
