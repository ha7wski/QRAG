"""
lexical_analyzer.py — LLM analysis of an Arabic root's occurrences (feature F2).

Takes a word, resolves its root and occurrences via LexicalRetriever, then
asks the LLM (with SYSTEM_PROMPT_LEXICAL) to produce a structured linguistic
analysis: definition, grammatical forms, semantic evolution, and the most
illustrative verses.
"""
from __future__ import annotations

import logging
import sys
import time
from collections.abc import Iterator
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from generation.llm_client import LLMClient  # noqa: E402
from generation.prompts import (  # noqa: E402
    SYSTEM_PROMPT_LEXICAL,
    build_lexical_user_message,
)
from retrieval.lexical_retriever import LexicalRetriever  # noqa: E402

# Verses sent to the LLM for analysis vs. returned as "key verses".
LLM_SAMPLE = 30
MAX_KEY_VERSES = 12

# Per-request timing; surfaces live in the backend log (start.sh tail -f).
logger = logging.getLogger("quran_rag.timing")


class LexicalAnalyzer:
    def __init__(
        self,
        retriever: LexicalRetriever | None = None,
        llm: LLMClient | None = None,
    ):
        self.retriever = retriever or LexicalRetriever()
        self.llm = llm or LLMClient()

    def _result(self, word: str) -> dict:
        return self.retriever.lookup(word, sample=LLM_SAMPLE)

    def analyze(self, word: str, language: str = "ar") -> dict:
        """Return {word, root, forms, occurrences_count, analysis, key_verses}."""
        t0 = time.perf_counter()
        result = self._result(word)
        t_lookup = time.perf_counter()
        if result["occurrences_count"] == 0:
            logger.info(
                "lexical: lookup=%.0fms | root=%s occurrences=0 (not found) | q=%r",
                (t_lookup - t0) * 1000, result["root"], word[:40],
            )
            return {
                "word": word,
                "root": result["root"],
                "forms": [],
                "occurrences_count": 0,
                "analysis": "",
                "key_verses": [],
                "found": False,
            }
        messages = [
            {
                "role": "user",
                "content": build_lexical_user_message(result, language),
            }
        ]
        analysis = self.llm.chat(SYSTEM_PROMPT_LEXICAL, messages)
        t_end = time.perf_counter()
        logger.info(
            "lexical: lookup=%.0fms generation=%.0fms total=%.0fms "
            "| root=%s occurrences=%d | q=%r",
            (t_lookup - t0) * 1000,
            (t_end - t_lookup) * 1000,
            (t_end - t0) * 1000,
            result["root"],
            result["occurrences_count"],
            word[:40],
        )
        return {
            "word": word,
            "root": result["root"],
            "forms": result["forms"],
            "occurrences_count": result["occurrences_count"],
            "analysis": analysis,
            "key_verses": result["verses"][:MAX_KEY_VERSES],
            "found": True,
        }

    def stream_analyze(self, word: str, language: str = "ar") -> Iterator[str]:
        """Stream the analysis text. Metadata is set on `self.last_result`."""
        t0 = time.perf_counter()
        result = self._result(word)
        t_lookup = time.perf_counter()
        self.last_result = result
        if result["occurrences_count"] == 0:
            logger.info(
                "lexical(stream): lookup=%.0fms | root=%s occurrences=0 (not found) | q=%r",
                (t_lookup - t0) * 1000, result["root"], word[:40],
            )
            return
        messages = [
            {
                "role": "user",
                "content": build_lexical_user_message(result, language),
            }
        ]
        t_first = None
        chunks = 0
        for chunk in self.llm.stream_chat(SYSTEM_PROMPT_LEXICAL, messages):
            if t_first is None:
                t_first = time.perf_counter()
            chunks += 1
            yield chunk
        t_end = time.perf_counter()
        ttft = ((t_first - t_lookup) * 1000) if t_first is not None else 0.0
        logger.info(
            "lexical(stream): lookup=%.0fms ttft=%.0fms generation=%.0fms "
            "total=%.0fms | root=%s occurrences=%d chunks=%d | q=%r",
            (t_lookup - t0) * 1000,
            ttft,
            (t_end - t_lookup) * 1000,
            (t_end - t0) * 1000,
            result["root"],
            result["occurrences_count"],
            chunks,
            word[:40],
        )


if __name__ == "__main__":
    analyzer = LexicalAnalyzer()
    if not analyzer.llm.health():
        print(f"⚠️  LLM not ready (model={analyzer.llm.model}).")
        raise SystemExit(1)
    out = analyzer.analyze("رحمة", language="fr")
    print(f"word={out['word']} root={out['root']} occurrences={out['occurrences_count']}")
    print("\nANALYSIS:\n", out["analysis"])
