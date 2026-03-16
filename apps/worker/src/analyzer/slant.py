"""Political slant scoring: embedding centroid + moral foundations + valence lexicon."""
import json
import os
from pathlib import Path
from typing import Optional

import numpy as np

DATA_DIR = Path(os.getenv("DATA_DIR", "/app/data"))

# ── Anchor loading ────────────────────────────────────────────────────────────

def _load_anchors() -> tuple[list[str], list[str], list[str]]:
    lib = (DATA_DIR / "anchors/liberal_anchors.txt").read_text().splitlines()
    con = (DATA_DIR / "anchors/conservative_anchors.txt").read_text().splitlines()
    neu = (DATA_DIR / "anchors/neutral_anchors.txt").read_text().splitlines()
    return lib, con, neu


def _load_valence() -> dict[str, float]:
    return json.loads((DATA_DIR / "anchors/political_valence_lexicon.json").read_text())


_anchor_centroids: Optional[tuple[np.ndarray, np.ndarray, np.ndarray]] = None
_valence_dict: Optional[dict[str, float]] = None


def _get_centroids():
    global _anchor_centroids
    if _anchor_centroids is None:
        from ..embedder.model import embed
        lib, con, neu = _load_anchors()
        _anchor_centroids = (
            np.mean(embed(lib), axis=0),
            np.mean(embed(con), axis=0),
            np.mean(embed(neu), axis=0),
        )
    return _anchor_centroids


def _get_valence():
    global _valence_dict
    if _valence_dict is None:
        _valence_dict = _load_valence()
    return _valence_dict


# ── Moral Foundations Dictionary (inline micro-lexicon) ───────────────────────

_MFD = {
    "care": ["harm", "care", "protect", "safe", "hurt", "abuse", "cruel", "kind"],
    "fairness": ["fair", "equal", "justice", "rights", "bias", "cheat", "reciproc"],
    "loyalty": ["loyal", "betray", "solidarity", "group", "team", "patriot"],
    "authority": ["authority", "obey", "respect", "tradition", "order", "rebel"],
    "purity": ["pure", "sacred", "disgust", "corrupt", "degrad", "sanctit"],
}


def _moral_foundations_score(text: str) -> dict[str, float]:
    words = text.lower().split()
    n = max(len(words), 1)
    scores = {}
    for foundation, terms in _MFD.items():
        count = sum(1 for w in words if any(t in w for t in terms))
        scores[foundation] = count / n
    return scores


# ── Composite scorer ──────────────────────────────────────────────────────────

def score_text(text: str) -> dict[str, float]:
    from ..embedder.model import embed_one

    snippet = text[:4000]
    vec = np.array(embed_one(snippet))

    # 1. Embedding similarity (50%)
    lib_c, con_c, neu_c = _get_centroids()
    lib_sim = float(np.dot(vec, lib_c))
    con_sim = float(np.dot(vec, con_c))
    # [-1, 1]: positive = liberal leaning
    emb_slant = (lib_sim - con_sim) / max(lib_sim + con_sim, 1e-9)

    # 2. Moral foundations (20%)
    mf = _moral_foundations_score(snippet)

    # 3. Political valence lexicon (30%)
    valence = _get_valence()
    words = snippet.lower().split()
    scores_v = [valence[w] for w in words if w in valence]
    pol_valence = float(np.mean(scores_v)) if scores_v else 0.0

    # Composite
    composite = 0.5 * emb_slant + 0.3 * pol_valence
    confidence = min(1.0, len(scores_v) / max(len(words) * 0.02, 1))

    return {
        "embedding_slant": round(emb_slant, 4),
        "moral_foundations_care": round(mf["care"], 6),
        "moral_foundations_fairness": round(mf["fairness"], 6),
        "moral_foundations_loyalty": round(mf["loyalty"], 6),
        "moral_foundations_authority": round(mf["authority"], 6),
        "moral_foundations_purity": round(mf["purity"], 6),
        "political_valence": round(pol_valence, 4),
        "composite_slant": round(composite, 4),
        "confidence": round(confidence, 4),
    }
