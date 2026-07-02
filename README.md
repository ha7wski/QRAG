# Quran RAG

A Retrieval-Augmented Generation system over the full Quran corpus, exposed
through a conversational chatbot. It lets anyone explore the Quranic text
intelligently: understand a word in its linguistic and theological context,
find every occurrence of a concept, read verses in their surrounding context,
and get answers sourced directly from the text — in Arabic, French, or English.

It offers a first, rigorous level of exploration that always cites its sources;
it is not a substitute for scholarly interpretation (tafsir).

> **Implementation status:** the MVP is complete end to end — ingestion
> pipeline, indexing, the base RAG pipeline (retrieval + generation), the
> FastAPI backend, the Next.js frontend, and the quality layer (query
> processing, HyDE, cross-encoder reranking). Two root-based study tools (Verse
> Study — exhaustive vocalized lookup; Lisan Analysis — LLM root analysis), plus
> single-verse / full-surah endpoints and pages (deep-linking), fully vocalized
> verse display, server-side session persistence (SQLite), and 👍/👎 answer
> feedback.

---

## Features

- **Talk to Quran (Chat Q&A)** — ask a question in Arabic, French, or English
  and get a streamed answer grounded in the retrieved verses, with every source
  cited (surah + ayah).
- **Verse Study** — two tabs over the Arabic corpus:
  - **Word in Verses (exhaustive root lookup)** — type a single Arabic word and
    see *every* verse that contains that word or any derivative of its root,
    grouped by surah with the matched word highlighted in place. Pure
    morphological lookup over the precomputed root index — no LLM, no vector
    search. Backed by `POST /verse-lookup`.
  - **Similar Verses** — type a phrase or a (partial) verse and get the closest
    verses, ranked. Candidates come from the union of a root channel
    (content-word roots → verses by IDF-weighted coverage) and BM25 on the
    stopword-cleaned query; a cross-encoder reranker then scores each candidate
    against the query, with a query-root-coverage step that keeps verses sharing
    the query's whole context (full-coverage / AND when the query has ≥2 roots).
    Arabic-only, no translations shown. Backed by `GET /search`.
- **Lisan Analysis (linguistic root analysis)** — look up an Arabic word by its
  trilateral root and get an LLM analysis of the shades of meaning the root
  carries across a representative sample of its occurrences.
- **Find Verse context & surah reading** — jump straight to any verse (surah
  picker + ayah number) with its surrounding context, and read a full surah as
  one continuous Arabic block. Verses deep-link via `/verse/{surah}/{ayah}` and
  `/surah/{number}`.
- **Session persistence & feedback** — conversations persist (browser +
  server-side SQLite) and each answer can be rated 👍/👎.
- **Fully vocalized display** — every verse shown in the UI is rendered with
  full diacritics (chakl), sourced from `data/raw/quran_chakl.csv`; the
  undiacritized text is kept for search/matching.
- **Multilingual throughout** — Arabic text is always shown in its original
  script; questions and answers work across ar/fr/en.

---

## Run it locally

The repo ships the source and the raw corpora — `data/raw/quran.csv`
(undiacritized, used for indexing/matching) and `data/raw/quran_chakl.csv`
(fully vocalized, used for display); the processed data and indexes are
generated locally. See **[`scripts/README.md`](scripts/README.md)**
for prerequisites, the one-time build, and the one-command launcher
(`./scripts/run.sh`).

---

## Project layout

```
quran-rag/
├── ingestion/        # Data pipeline: parse → normalize → enrich → morphology
├── indexing/         # Embeddings, Qdrant, BM25, hybrid (RRF) search
├── retrieval/        # Hybrid retrieval + quality layer (query proc, HyDE, rerank)
├── generation/       # RAG orchestration + LLM client
├── api/              # FastAPI backend (HTTP layer)
├── frontend/         # Next.js UI
├── data/
│   ├── raw/          # quran.csv (indexing) + quran_chakl.csv (vocalized display)
│   └── processed/    # generated JSON / indexes
└── scripts/          # setup / run / ingest / translation helpers
```

Four decoupled layers — ingestion → indexing → retrieval → generation — each
replaceable without refactoring the others, wired together and exposed over HTTP
by `api/` and consumed by the Next.js `frontend/`.

---

## How retrieval works

- **Dense:** verses embedded with a multilingual E5 model, stored in Qdrant
  (cosine). Payload indexes on `surah_number`, `period`, `juz` enable filtering.
- **Sparse:** BM25Okapi over normalized Arabic text + translations.
- **Hybrid:** Reciprocal Rank Fusion combines the top-20 of each retriever:
  `score = 1/(60 + rank_dense) + 1/(60 + rank_sparse)`.

French (Hamidullah) and English (Sahih International) translations are indexed
alongside the Arabic text, so the embedded passage is
`passage: {text_ar_clean} {translation_fr} {translation_en}` and BM25 covers all
three. Indexing translations raised retrieval hit-rate@10 from ~0.70 to ~0.90 in
testing.

### Quality layer

These shape the **retrieval query** only; the LLM always answers the user's
original question against the retrieved context. All three are wired into
`generation/chat_engine.py` behind env toggles.

- **Query processing** (`retrieval/query_processor.py`, `QUERY_PROCESSOR_ENABLED`,
  on by default): language detection, lexical/root detection, light
  morphology-based expansion (appends Arabic root surface-forms to the query),
  and inline filter detection (e.g. "makki" → `period=makkiyya`). Cheap, no LLM.
- **HyDE** (`retrieval/hyde.py`, `HYDE_ENABLED`, off by default): the LLM writes
  a hypothetical verse for the query and it is appended to the retrieval query.
  Adds one LLM call (latency) but rescues abstract questions — e.g. "creation of
  the heavens and the earth" and "kindness to parents" went from 0 gold hits to
  2–3 when HyDE was enabled.
- **Reranking** (`retrieval/reranker.py`): a cross-encoder reorders the top-20
  candidates. Opt-in via `RERANK_ENABLED=1`. The default model is the
  multilingual `BAAI/bge-reranker-v2-m3` (ar/fr/en), which vastly outperforms
  the old English-only `ms-marco`. In testing it improved every retrieval metric
  (e.g. recall@10 ~0.28→0.34, hit-rate 0.80→0.84, MRR 0.43→0.56). Recommended for
  quality; kept **off by default** only because of its cost (~2.3 GB + per-query
  CPU latency). (Lighter alternative: `BAAI/bge-reranker-base`.)

---

## Configuration

All runtime settings live in `.env` (see `.env.example`):

- **LLM:** `LLM_PROVIDER` (`ollama` | `anthropic`), `OLLAMA_MODEL` /
  `OLLAMA_BASE_URL` or `ANTHROPIC_API_KEY` / `ANTHROPIC_MODEL`.
- **Vector DB:** `QDRANT_URL` (use `http://localhost:6333` on the host,
  `http://qdrant:6333` in Docker), `QDRANT_COLLECTION`.
- **Embedding:** `EMBEDDING_MODEL`, `EMBEDDING_DEVICE` (`auto`/`cpu`/`cuda`/`mps`),
  `EMBEDDING_BATCH_SIZE`.
- **Quality toggles:** `QUERY_PROCESSOR_ENABLED` (on), `HYDE_ENABLED` (off),
  `RERANK_ENABLED` (off).
- **App:** `CORS_ORIGINS`, `LOG_LEVEL`.
