"""Size-cap + content-type-mismatch regression tests for the collector."""
from apps.collector.src.collectors.base import (
    MAX_CONTENT_BYTES,
    TRUNCATION_MARKER,
    enforce_size_cap,
    looks_like_pdf,
)


def test_small_content_unchanged():
    s = "hello" * 1000
    assert enforce_size_cap(s) == s


def test_content_at_cap_unchanged():
    s = "x" * MAX_CONTENT_BYTES
    assert enforce_size_cap(s) == s
    assert len(enforce_size_cap(s)) == MAX_CONTENT_BYTES


def test_oversize_content_truncated_with_marker():
    bloat = "x" * (MAX_CONTENT_BYTES + 10_000)
    out = enforce_size_cap(bloat, slug="opus46_repro")
    assert len(out) == MAX_CONTENT_BYTES + len(TRUNCATION_MARKER)
    assert out.endswith(TRUNCATION_MARKER)
    assert out[:MAX_CONTENT_BYTES] == "x" * MAX_CONTENT_BYTES


def test_12mb_regression_bounded():
    """Reproduces the opus46 blow-up: 12,374,160 chars of garbage."""
    bloat = "\x00\x01\x02\x03" * 3_093_540
    assert len(bloat) > 12_000_000
    out = enforce_size_cap(bloat, slug="anthropic_opus46_card")
    assert len(out) < 600_000
    assert out.endswith(TRUNCATION_MARKER)


def test_looks_like_pdf_detects_magic():
    assert looks_like_pdf(b"%PDF-1.7\n...")
    assert looks_like_pdf(b"  %PDF-1.4 ...")
    assert not looks_like_pdf(b"<html><body>not a pdf</body></html>")
    assert not looks_like_pdf(b"")
