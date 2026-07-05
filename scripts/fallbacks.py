"""
Simple fallback loader and selector for SCARAG.

This script loads `fallback_template.json` from the repository root by default (or from the path
specified by the FALLBACK_PATH environment variable) and selects a fallback response based on
string-similarity matching and optional retrieval confidence.

Usage example:
  python scripts/fallbacks.py "how do i run tests" --conf 0.3

The selection strategy here is intentionally simple and meant as a scaffold:
  - If an explicit FAQ mapping is provided (as a dict mapping normalized keys -> fallback id), it is
    consulted first (not implemented in this scaffold but the API accepts an optional faq_map).
  - Next, an intent-based best-match using difflib.SequenceMatcher is attempted.
  - If the best-match meets a threshold and the entry's confidence_threshold allows it, the entry
    is returned.
  - Otherwise, a generic abstain/suggest fallback is returned.

This file is a starting point — teams should replace the matching logic with a more robust
intent-matching system (semantic search, embeddings, or a production fuzzy matcher) as needed.
"""

from __future__ import annotations

import json
import os
import sys
from dataclasses import dataclass
from difflib import SequenceMatcher
from typing import Any, Dict, List, Optional

FALLBACK_ENV = "FALLBACK_PATH"
DEFAULT_FALLBACK_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "fallback_template.json")


@dataclass
class FallbackEntry:
    id: str
    question_examples: List[str]
    response: str
    type: str
    confidence_threshold: Optional[float] = None
    notes: Optional[str] = None


def load_fallbacks(path: Optional[str] = None) -> List[FallbackEntry]:
    path = path or os.environ.get(FALLBACK_ENV, DEFAULT_FALLBACK_PATH)
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    entries = []
    for item in data:
        entries.append(
            FallbackEntry(
                id=item.get("id"),
                question_examples=item.get("question_examples", []),
                response=item.get("response", ""),
                type=item.get("type", "suggest"),
                confidence_threshold=item.get("confidence_threshold"),
                notes=item.get("notes"),
            )
        )
    return entries


def similarity(a: str, b: str) -> float:
    return SequenceMatcher(None, a, b).ratio()


def best_match(user_text: str, fallbacks: List[FallbackEntry]) -> Optional[Dict[str, Any]]:
    user = user_text.lower().strip()
    best: Optional[FallbackEntry] = None
    best_score = 0.0
    for fb in fallbacks:
        for ex in fb.question_examples:
            score = similarity(user, ex.lower())
            if score > best_score:
                best_score = score
                best = fb
    if best is None:
        return None
    return {"fallback": best, "score": best_score}


def select_fallback(user_text: str, retrieval_confidence: Optional[float] = None, faq_map: Optional[Dict[str, str]] = None) -> str:
    """Select a fallback response.

    - user_text: the user's raw question
    - retrieval_confidence: numeric score from retrieval or model (lower means less confident)
    - faq_map: optional mapping of normalized question -> fallback_id to prioritize explicit FAQ entries
    """
    fallbacks = load_fallbacks()

    # 1) FAQ mapping (explicit overrides)
    if faq_map:
        key = user_text.lower().strip()
        fb_id = faq_map.get(key)
        if fb_id:
            for fb in fallbacks:
                if fb.id == fb_id:
                    return fb.response

    # 2) Intent-based best match
    match = best_match(user_text, fallbacks)
    if match:
        fb: FallbackEntry = match["fallback"]
        score: float = match["score"]
        # Heuristic threshold -- could be configurable per-entry
        required_score = 0.6
        if score >= required_score:
            ct = fb.confidence_threshold
            if ct is None or (retrieval_confidence is not None and retrieval_confidence <= ct) or retrieval_confidence is None:
                return fb.response

    # 3) Generic fallback
    generic = next((f for f in fallbacks if f.id == "generic_fallback"), None)
    if generic:
        return generic.response

    return "I don't have a confident answer right now; would you like me to try a broader search or show related resources?"


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser("fallbacks")
    parser.add_argument("query", help="User question to test against fallbacks")
    parser.add_argument("--conf", type=float, default=None, help="Optional retrieval confidence (lower is less confident)")
    parser.add_argument("--path", type=str, default=None, help="Path to fallback_template.json (overrides env var)")
    args = parser.parse_args()

    if args.path:
        os.environ[FALLBACK_ENV] = args.path

    resp = select_fallback(args.query, retrieval_confidence=args.conf)
    print(resp)
