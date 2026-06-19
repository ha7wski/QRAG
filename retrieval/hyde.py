"""
hyde.py — Hypothetical Document Embeddings.

For abstract or complex questions, dense retrieval improves if we first ask
the LLM to write a short hypothetical Quranic passage answering the question,
then embed THAT instead of (or in addition to) the raw query. The generated
text lives in the same space as the indexed verses, which boosts recall.

The generated text is hypothetical and is never shown to the user or cited.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from generation.llm_client import LLMClient  # noqa: E402

HYDE_SYSTEM = "You are an expert on the Quran. Be concise."

HYDE_PROMPT = """A user is looking for Quranic verses about the following topic:
{query}

Write a short passage (2-3 sentences) that reads like a Quranic verse on this
topic: Arabic text followed by a brief English gloss. Do NOT quote real verses
or add references — produce a plausible hypothetical text only."""


class HyDE:
    def __init__(self, llm: LLMClient | None = None):
        self.llm = llm or LLMClient()

    def generate(self, query: str) -> str:
        """Return a hypothetical verse-like document for the query."""
        messages = [{"role": "user", "content": HYDE_PROMPT.format(query=query)}]
        return self.llm.chat(HYDE_SYSTEM, messages).strip()


if __name__ == "__main__":
    h = HyDE()
    if not h.llm.health():
        print(f"⚠️  LLM not ready (model={h.llm.model}).")
        raise SystemExit(1)
    print(h.generate("the importance of patience in hardship"))
