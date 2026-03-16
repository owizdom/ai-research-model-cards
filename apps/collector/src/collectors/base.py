"""Async HTTP utilities for document collection."""
import hashlib
import re
from dataclasses import dataclass
from io import BytesIO
from typing import Optional

import httpx
from bs4 import BeautifulSoup
from markdownify import markdownify as md

USER_AGENT = "Mozilla/5.0 AI-Safety-Research-Bot/1.0"
DEFAULT_HEADERS = {"User-Agent": USER_AGENT, "Accept-Language": "en-US,en;q=0.9"}


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
    r = await client.get(url, headers=DEFAULT_HEADERS, follow_redirects=True, timeout=30.0)
    r.raise_for_status()
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
    from pypdf import PdfReader
    r = await client.get(url, headers=DEFAULT_HEADERS, follow_redirects=True, timeout=60.0)
    r.raise_for_status()
    reader = PdfReader(BytesIO(r.content))
    return "\n\n".join(p.extract_text() for p in reader.pages if p.extract_text())
