"""
embedder_ar.py — The text contract of the Arabic dense collection (`quran_verses_ar`).

Loads NO model. The encoder is the process's one `indexing.embedder.Embedder`
(`EMBEDDING_MODEL`, multilingual-e5-large-instruct), shared with the chat path; this
module only says what text that encoder is given on each side, so the collection's
builder and every reader format identically:

  - passage: `normalize_search(text_ar)`, no prefix — Arabic only, hamza folded not
    deleted (never `text_ar_clean`, which has hamza deleted);
  - query:   `Instruct: {INSTRUCTION}\\nQuery: {normalize_search(query)}`.

That is the model card's instruct format (documents bare, queries instructed), not the
`query: `/`passage: ` convention `Embedder` applies for the older collection. It was
measured in change `arabic-retrieval-models` (config A: phrase nDCG@10 0.722 against
0.310 for the deployed format), and INSTRUCTION is the exact string measured — changing
it, or the normalizer, changes `FORMAT`, and a collection built under another FORMAT
must be rebuilt rather than queried.

The chat path can adopt this collection later by querying it with `query_text` — the
points carry the same ids and payload as `quran_verses`.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from arabic_text import normalize_search  # noqa: E402

INSTRUCTION = "Given an Arabic query, retrieve Quranic verses relevant to it"
FORMAT = "e5-instruct-card/normalize_search/v1"
# The encoder the format was measured with. The builder refuses another one, and a
# reader abstains when the shared embedder is not this model.
EXPECTED_MODEL = "intfloat/multilingual-e5-large-instruct"
DEFAULT_COLLECTION = "quran_verses_ar"


def passage_text(verse: dict) -> str:
    """The text embedded for a verse: its raw Arabic, search-normalized, no prefix."""
    return normalize_search(verse.get("text_ar", ""))


def query_text(query: str) -> str:
    """The text embedded for a query, in the model card's instruct format."""
    return f"Instruct: {INSTRUCTION}\nQuery: {normalize_search(query)}"
