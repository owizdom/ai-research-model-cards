"""Wayback Machine CDX integration for historical document snapshots."""
import asyncio
from datetime import date, datetime
from typing import Optional

import httpx
from bs4 import BeautifulSoup
from markdownify import markdownify as md

from packages.pipeline_config import HTTP_TIMEOUT_DEFAULT_S

from .base import HistoricalVersion, clean_markdown, compute_hash, word_count, DEFAULT_HEADERS
from .registry import Source

CDX = "http://web.archive.org/cdx/search/cdx"
WB_BASE = "https://web.archive.org/web"


async def get_snapshots(url: str, client: httpx.AsyncClient, from_year: int = 2021) -> list[dict]:
    params = {
        "url": url, "output": "json", "fl": "timestamp,statuscode,digest",
        "filter": "statuscode:200", "from": f"{from_year}0101", "collapse": "digest",
    }
    try:
        r = await client.get(CDX, params=params, headers=DEFAULT_HEADERS, timeout=HTTP_TIMEOUT_DEFAULT_S)
        r.raise_for_status()
        data = r.json()
        if not data or len(data) < 2:
            return []
        keys = data[0]
        return [dict(zip(keys, row)) for row in data[1:]]
    except Exception as e:
        print(f"[wayback] CDX error {url}: {e}")
        return []


async def fetch_snapshot(wayback_url: str, client: httpx.AsyncClient) -> str:
    r = await client.get(wayback_url, headers=DEFAULT_HEADERS, follow_redirects=True, timeout=HTTP_TIMEOUT_DEFAULT_S)
    r.raise_for_status()
    soup = BeautifulSoup(r.text, "html.parser")
    for el in soup.select("#wm-ipp-base, #wm-ipp, .wb-autocomplete-suggestions"):
        el.decompose()
    for el in soup(["script", "style", "nav", "footer", "header", "aside"]):
        el.decompose()
    for sel in ["article", "main", ".content", "#content"]:
        content = soup.select_one(sel)
        if content:
            return md(str(content), heading_style="ATX")
    body = soup.find("body")
    return md(str(body) if body else r.text, heading_style="ATX")


async def get_historical(source: Source, client: httpx.AsyncClient, min_gap_days: int = 30) -> list[HistoricalVersion]:
    snapshots = await get_snapshots(source.url, client)
    versions: list[HistoricalVersion] = []
    last_date: Optional[date] = None
    seen: set[str] = set()

    for snap in snapshots:
        try:
            ts = snap["timestamp"]
            snap_date = datetime.strptime(ts, "%Y%m%d%H%M%S").date()
            if last_date and (snap_date - last_date).days < min_gap_days:
                continue
            wb_url = f"{WB_BASE}/{ts}/{source.url}"
            content = clean_markdown(await fetch_snapshot(wb_url, client))
            if not content.strip():
                continue
            h = compute_hash(content)
            if h in seen:
                continue
            seen.add(h)
            last_date = snap_date
            versions.append(HistoricalVersion(
                version_date=snap_date.isoformat(), content_md=content,
                content_hash=h, wayback_url=wb_url, word_count=word_count(content),
            ))
            await asyncio.sleep(1.0)
        except Exception as e:
            print(f"[wayback] {source.slug} @ {snap.get('timestamp')}: {e}")
    return versions
