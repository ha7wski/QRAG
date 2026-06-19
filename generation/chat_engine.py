"""
chat_engine.py — RAG conversation engine.

Orchestrates the pipeline:
    question
      → QueryProcessor (language, filters, Arabic-root expansion)
      → [optional] HyDE (hypothetical verse to enrich the retrieval query)
      → hybrid retrieval (+ optional rerank, + neighbor context)
      → LLM generation
      → answer + sources

QueryProcessor and HyDE only shape the *retrieval query*; the LLM always
answers the user's ORIGINAL question against the retrieved context.

Toggles (env):
    QUERY_PROCESSOR_ENABLED  default on  — cheap, deterministic
    HYDE_ENABLED             default off — adds an LLM call (latency)
    RERANK_ENABLED           default off — cross-encoder reranking

Usage:
    python generation/chat_engine.py "What does the Quran say about patience?"
"""
from __future__ import annotations

import logging
import os
import sys
import time
from collections.abc import Iterator
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from generation.llm_client import LLMClient  # noqa: E402
from generation.prompts import (  # noqa: E402
    SYSTEM_PROMPT_CHAT,
    build_chat_user_message,
)
from retrieval.retriever import Retriever  # noqa: E402

DEFAULT_TOP_K = 5
DEFAULT_CONTEXT_WINDOW = 1
# Number of Arabic root surface-forms appended to the retrieval query.
MAX_EXPANSION_TERMS = 6

# Per-request timing is logged here; it surfaces in the backend log (and thus
# in `tail -f` from local-dev/start.sh).
logger = logging.getLogger("quran_rag.timing")


def _env_on(name: str, default: str = "0") -> bool:
    return os.getenv(name, default).lower() in ("1", "true", "yes")


def _maybe_reranker():
    """Build a cross-encoder reranker if RERANK_ENABLED is truthy, else None."""
    if _env_on("RERANK_ENABLED"):
        from retrieval.reranker import Reranker

        return Reranker()
    return None


class ChatEngine:
    def __init__(
        self,
        retriever: Retriever | None = None,
        llm: LLMClient | None = None,
        top_k: int = DEFAULT_TOP_K,
        context_window: int = DEFAULT_CONTEXT_WINDOW,
    ):
        self.retriever = retriever or Retriever(reranker=_maybe_reranker())
        self.llm = llm or LLMClient()
        self.top_k = top_k
        self.context_window = context_window

        # QueryProcessor: on by default (cheap, no LLM).
        self.query_processor = None
        if _env_on("QUERY_PROCESSOR_ENABLED", "1"):
            from retrieval.query_processor import QueryProcessor

            self.query_processor = QueryProcessor()

        # HyDE: off by default (extra LLM call). Reuses the chat LLM client.
        self.hyde = None
        if _env_on("HYDE_ENABLED"):
            from retrieval.hyde import HyDE

            self.hyde = HyDE(llm=self.llm)

    def _retrieval_query(
        self, question: str, filters: dict | None
    ) -> tuple[str, dict]:
        """Build the (possibly enriched) retrieval query and merged filters.

        - QueryProcessor adds detected filters (e.g. period) and Arabic-root
          surface forms (expansion).
        - HyDE appends a hypothetical verse to pull in on-topic vocabulary.
        Caller-supplied filters take precedence over detected ones.
        """
        query = question
        detected: dict = {}

        if self.query_processor is not None:
            pq = self.query_processor.process(question)
            detected = pq.filters or {}
            if pq.expanded_terms:
                extra = " ".join(pq.expanded_terms[:MAX_EXPANSION_TERMS])
                query = f"{question} {extra}"

        if self.hyde is not None:
            try:
                query = f"{query}\n{self.hyde.generate(question)}"
            except Exception:
                pass  # HyDE is best-effort; fall back to the plain query

        merged = {**detected, **(filters or {})}
        return query, (merged or None)

    def _prepare(
        self, question: str, filters: dict | None, history: list[dict] | None
    ) -> tuple[list[dict], list[dict], list[dict]]:
        """Retrieve sources/context and build the LLM message list."""
        retrieval_query, merged_filters = self._retrieval_query(question, filters)
        hits, context = self.retriever.retrieve_with_context(
            retrieval_query,
            top_k=self.top_k,
            window=self.context_window,
            filters=merged_filters,
        )
        # The LLM answers the ORIGINAL question, with the retrieved context.
        messages = list(history or [])
        messages.append(
            {"role": "user", "content": build_chat_user_message(question, context)}
        )
        return hits, context, messages

    def _flags(self) -> str:
        return (
            f"qp={'on' if self.query_processor else 'off'} "
            f"hyde={'on' if self.hyde else 'off'} "
            f"rerank={'on' if self.retriever.reranker else 'off'}"
        )

    def chat(
        self,
        question: str,
        filters: dict | None = None,
        history: list[dict] | None = None,
    ) -> dict:
        """Run the full pipeline and return {answer, sources}."""
        t0 = time.perf_counter()
        hits, _, messages = self._prepare(question, filters, history)
        t_ret = time.perf_counter()
        answer = self.llm.chat(SYSTEM_PROMPT_CHAT, messages)
        t_end = time.perf_counter()
        logger.info(
            "chat: retrieval=%.0fms generation=%.0fms total=%.0fms "
            "| sources=%d | %s | q=%r",
            (t_ret - t0) * 1000,
            (t_end - t_ret) * 1000,
            (t_end - t0) * 1000,
            len(hits),
            self._flags(),
            question[:60],
        )
        return {"answer": answer, "sources": hits}

    def stream_chat(
        self,
        question: str,
        filters: dict | None = None,
        history: list[dict] | None = None,
    ) -> Iterator[str]:
        """Stream answer chunks. Sources are available via `last_sources`.

        Logs a per-request timing summary (retrieval, time-to-first-token,
        total generation) once the stream is exhausted.
        """
        t0 = time.perf_counter()
        hits, _, messages = self._prepare(question, filters, history)
        t_ret = time.perf_counter()
        self.last_sources = hits

        t_first = None
        chunks = 0
        for chunk in self.llm.stream_chat(SYSTEM_PROMPT_CHAT, messages):
            if t_first is None:
                t_first = time.perf_counter()
            chunks += 1
            yield chunk
        t_end = time.perf_counter()

        ttft = ((t_first - t_ret) * 1000) if t_first is not None else 0.0
        logger.info(
            "chat(stream): retrieval=%.0fms ttft=%.0fms generation=%.0fms "
            "total=%.0fms | sources=%d chunks=%d | %s | q=%r",
            (t_ret - t0) * 1000,
            ttft,
            (t_end - t_ret) * 1000,
            (t_end - t0) * 1000,
            len(hits),
            chunks,
            self._flags(),
            question[:60],
        )


def _cli() -> int:
    if len(sys.argv) < 2:
        print('Usage: python generation/chat_engine.py "your question"')
        return 2
    question = " ".join(sys.argv[1:])

    engine = ChatEngine()
    if not engine.llm.health():
        print(
            f"⚠️  LLM backend not ready (provider={engine.llm.provider}, "
            f"model={engine.llm.model}). For Ollama, run:\n"
            f"    docker compose up -d ollama && "
            f"docker exec quran-ollama ollama pull {engine.llm.model}"
        )
        return 1

    print(f"Q: {question}\n")
    print("A: ", end="", flush=True)
    for chunk in engine.stream_chat(question):
        print(chunk, end="", flush=True)
    print("\n\nSources:")
    for s in engine.last_sources:
        print(
            f"  [{s['id']}] Surah {s['surah_name_en']} ({s['surah_number']}), "
            f"Verse {s['ayah_number']}  score={s['score']:.4f}"
        )
        print(f"        {s['text_ar']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(_cli())
