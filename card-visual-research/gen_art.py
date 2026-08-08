#!/usr/bin/env python3
"""Generate card art with Gemini, in the house style from art-prompts.md.

Every existing piece was made by hand-pasting prompts into Gemini 2.5 Flash
Image; this does the same call from the repo so new cards and the pack cover
can be regenerated reproducibly. Reads GEMINI_API_KEY from .env.

    python3 gen_art.py --prompt-file p.txt --out cards/_pack/x/art/hero.png
    python3 gen_art.py --prompt "..." --out path.png --n 3
"""
from __future__ import annotations

import argparse
import base64
import json
import os
import sys
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent
REPO = ROOT.parent
MODEL = os.environ.get("GEMINI_IMAGE_MODEL", "gemini-2.5-flash-image")
URL = "https://generativelanguage.googleapis.com/v1beta/models/{m}:generateContent?key={k}"


def api_key() -> str:
    if os.environ.get("GEMINI_API_KEY"):
        return os.environ["GEMINI_API_KEY"]
    for line in (REPO / ".env").read_text().splitlines():
        if line.startswith("GEMINI_API_KEY="):
            return line.split("=", 1)[1].strip().strip('"').strip("'")
    sys.exit("GEMINI_API_KEY not found in env or .env")


def generate(prompt: str, out: Path, n: int = 1) -> int:
    key = api_key()
    body = json.dumps({"contents": [{"parts": [{"text": prompt}]}]}).encode()
    written = 0
    for i in range(n):
        req = urllib.request.Request(
            URL.format(m=MODEL, k=key), data=body,
            headers={"Content-Type": "application/json"})
        try:
            with urllib.request.urlopen(req, timeout=300) as r:
                data = json.loads(r.read())
        except urllib.error.HTTPError as e:
            sys.exit(f"gemini {e.code}: {e.read()[:400].decode(errors='replace')}")

        parts = data.get("candidates", [{}])[0].get("content", {}).get("parts", [])
        img = next((p["inlineData"]["data"] for p in parts if "inlineData" in p), None)
        if not img:
            txt = " ".join(p.get("text", "") for p in parts)[:300]
            print(f"  no image returned (attempt {i+1}): {txt}")
            continue
        dest = out if n == 1 else out.with_name(f"{out.stem}-{i+1}{out.suffix}")
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(base64.b64decode(img))
        print(f"  wrote {dest} ({dest.stat().st_size:,} bytes)")
        written += 1
    return written


def main(argv):
    p = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    p.add_argument("--prompt")
    p.add_argument("--prompt-file")
    p.add_argument("--out", required=True)
    p.add_argument("--n", type=int, default=1, help="variants to generate")
    a = p.parse_args(argv)
    prompt = a.prompt or Path(a.prompt_file).read_text()
    return 0 if generate(prompt, Path(a.out), a.n) else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
