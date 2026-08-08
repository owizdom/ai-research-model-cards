"""Async HTTP utilities for document collection."""
import hashlib
import re
from dataclasses import dataclass
from io import BytesIO
from typing import Optional

import httpx
from bs4 import BeautifulSoup
from markdownify import markdownify as md

from packages.pipeline_config import HTTP_TIMEOUT_BULK_S, HTTP_TIMEOUT_DEFAULT_S

USER_AGENT = "Mozilla/5.0 AI-Safety-Research-Bot/1.0"
DEFAULT_HEADERS = {"User-Agent": USER_AGENT, "Accept-Language": "en-US,en;q=0.9"}

MAX_CONTENT_BYTES = 1_200_000
"""The cap was 500,000, which silently decapitated the two longest cards.

Model cards put their benchmark tables near the END, behind the safety prose:
Claude Fable 5's SWE-bench table is section 8.2 of a 624,000-char document, and
the Gemini 1.5 report is 565,000. Both stored at exactly 500,062 chars, so the
tables were cut off before extraction ever saw them and Fable 5 came back with
no scores at all.

1.2M clears the largest card in the corpus with room to spare. Raise it before
adding a longer one rather than after."""
TRUNCATION_MARKER = "\n\n[... TRUNCATED BY COLLECTOR — content exceeded size cap ...]"
PDF_MAGIC = b"%PDF-"


class ContentTypeMismatch(Exception):
    """Fetch bytes don't match the declared method (e.g. PDF on html)."""


def looks_like_pdf(data: bytes) -> bool:
    return data[:8].lstrip().startswith(PDF_MAGIC)


def enforce_size_cap(content: str, slug: str = "<unknown>", limit: int = MAX_CONTENT_BYTES) -> str:
    if len(content) <= limit:
        return content
    print(
        f"[collector] WARNING {slug}: content exceeded cap — "
        f"{len(content):,} chars > {limit:,}; truncating",
        flush=True,
    )
    return content[:limit] + TRUNCATION_MARKER


@dataclass
class CollectedDocument:
    slug: str
    lab_slug: str
    title: str
    doc_type: str
    source_url: str
    content_md: str
    content_hash: str
    word_count: int


@dataclass
class HistoricalVersion:
    version_date: str
    content_md: str
    content_hash: str
    wayback_url: str
    word_count: int


def compute_hash(content: str) -> str:
    return hashlib.sha256(content.encode("utf-8")).hexdigest()


def clean_markdown(text: str) -> str:
    text = re.sub(r'\n{3,}', '\n\n', text)
    return '\n'.join(line.rstrip() for line in text.split('\n')).strip()


def word_count(text: str) -> int:
    return len(text.split())


async def html_to_markdown(url: str, client: httpx.AsyncClient, selector: Optional[str] = None) -> str:
    r = await client.get(url, headers=DEFAULT_HEADERS, follow_redirects=True, timeout=HTTP_TIMEOUT_DEFAULT_S)
    r.raise_for_status()
    if looks_like_pdf(r.content) or "application/pdf" in r.headers.get("content-type", "").lower():
        raise ContentTypeMismatch(
            f"{url} returned PDF content but source declared method=html; "
            "re-register with method=pdf"
        )
    soup = BeautifulSoup(r.text, "html.parser")
    for el in soup(["script", "style", "nav", "footer", "header", "aside"]):
        el.decompose()
    if selector:
        content = soup.select_one(selector)
        if content:
            return md(str(content), heading_style="ATX")
    for sel in ["article", "main", '[role="main"]', ".content", "#content", ".post-content"]:
        content = soup.select_one(sel)
        if content:
            return md(str(content), heading_style="ATX")
    body = soup.find("body")
    return md(str(body) if body else r.text, heading_style="ATX")


async def pdf_to_text(url: str, client: httpx.AsyncClient) -> str:
    """Text with the column layout intact.

    pypdf drops column geometry, and the benchmark tables are the whole point of
    these documents. A Gemini 1.5 table came through as
    "39.9% 0-shot 55.8% 0-shot 53.6% 0-shot" with the model names detached from
    their numbers, and Claude 3's Table 1 lost the header saying which of
    86.8 / 79.0 / 75.2 is Opus, Sonnet and Haiku. The extractor then attributed
    all 22 rows of that report to Opus, so Sonnet and Haiku were published with
    Opus's GPQA of 50.4 when they score 40.4 and 33.3.

    `pdftotext -layout` preserves the x-positions, which is what
    packages/table_extract.py needs to read a row by column. Falls back to pypdf
    if poppler is not installed, so ingestion still works, but the tables will be
    unreliable again.
    """
    import shutil
    import subprocess
    import tempfile

    r = await client.get(url, headers=DEFAULT_HEADERS, follow_redirects=True, timeout=HTTP_TIMEOUT_BULK_S)
    r.raise_for_status()

    if shutil.which("pdftotext"):
        with tempfile.NamedTemporaryFile(suffix=".pdf") as fh:
            fh.write(r.content)
            fh.flush()
            out = subprocess.run(
                ["pdftotext", "-layout", fh.name, "-"],
                capture_output=True, timeout=180,
            )
            if out.returncode == 0 and out.stdout.strip():
                return out.stdout.decode("utf-8", "replace")

    from pypdf import PdfReader
    reader = PdfReader(BytesIO(r.content))
    return "\n\n".join(p.extract_text() for p in reader.pages if p.extract_text())


async def arxiv_pdf_to_text(url: str, client: httpx.AsyncClient) -> str:
    """Convert arxiv abstract URL to PDF URL and extract full paper text."""
    pdf_url = url.replace("/abs/", "/pdf/")
    if not pdf_url.endswith(".pdf"):
        pdf_url += ".pdf"
    return await pdf_to_text(pdf_url, client)
