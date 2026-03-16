"""Fetch all sources concurrently."""
import asyncio
import httpx
from .base import CollectedDocument, html_to_markdown, pdf_to_text, clean_markdown, compute_hash, word_count
from .registry import SOURCES, Source


async def fetch_source(source: Source, client: httpx.AsyncClient) -> CollectedDocument | None:
    try:
        if source.method == "html":
            content = await html_to_markdown(source.url, client, source.selector)
        elif source.method == "pdf":
            content = await pdf_to_text(source.url, client)
        elif source.method == "raw":
            resp = await client.get(source.url)
            resp.raise_for_status()
            content = resp.text
        else:
            return None
        content = clean_markdown(content)
        if not content.strip():
            return None
        return CollectedDocument(
            slug=source.slug, lab_slug=source.lab_slug, title=source.title,
            doc_type=source.doc_type, source_url=source.url,
            content_md=content, content_hash=compute_hash(content), word_count=word_count(content),
        )
    except Exception as e:
        print(f"[fetch] {source.slug}: {e}")
        return None


async def fetch_all(concurrency: int = 5) -> list[CollectedDocument]:
    sem = asyncio.Semaphore(concurrency)

    async def _fetch(source: Source, client: httpx.AsyncClient):
        async with sem:
            return await fetch_source(source, client)

    headers = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.5",
    }
    async with httpx.AsyncClient(timeout=60.0, headers=headers, follow_redirects=True) as client:
        results = await asyncio.gather(*[_fetch(s, client) for s in SOURCES], return_exceptions=True)

    return [r for r in results if isinstance(r, CollectedDocument)]
