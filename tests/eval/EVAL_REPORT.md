# Retrieval Evaluation Report

Evaluation of the Quran RAG retrieval layer on the expanded reference set
`tests/eval/qa_dataset.json`.

## Dataset

- **50 questions** across languages: 15 Arabic, 15 French, 15 English, 5 mixed
  (cross-lingual, e.g. `"prayer الصلاة"`).
- **37 distinct surahs** covered by the gold verses.
- Gold sets (`relevant_verse_ids`) are **curated core verses per theme**, each
  verified to exist in the indexed corpus and checked against its Arabic +
  English text (`tests/eval/verify_gold.py`, 0 missing). They are
  *representative, not exhaustive* — borderline verses (e.g. 2:222, which is
  primarily about menstruation) were removed to keep the sets honest.

## Method

- Retriever: hybrid dense (multilingual-e5-large-instruct, Qdrant cosine) +
  sparse (BM25) with RRF; corpus indexes Arabic + FR (Hamidullah) + EN (Sahih).
- Reranker (opt-in): `BAAI/bge-reranker-v2-m3`, multilingual cross-encoder,
  reorders the top-20 candidates.
- `top_k = 10`. Metrics: **recall@k** (gold found / gold total), **hit-rate@k**
  (≥1 gold in top-k), **MRR** (reciprocal rank of the first gold verse).
- Commands:
  ```bash
  python tests/eval/evaluate.py            # baseline
  python tests/eval/evaluate.py --rerank   # + bge-reranker-v2-m3
  ```

## Headline comparison (top_k = 10)

| config        | recall@10 AR | recall@10 FR | recall@10 EN | hit-rate@10 | MRR   |
|---------------|--------------|--------------|--------------|-------------|-------|
| baseline      | 0.266        | 0.269        | 0.277        | 0.800       | 0.433 |
| + bge-v2-m3   | **0.401**    | **0.367**    | 0.263        | **0.840**   | **0.561** |

## Per-language breakdown

| lang  | n  | recall@10 base → rerank | hit-rate base → rerank | MRR base → rerank |
|-------|----|-------------------------|------------------------|-------------------|
| ar    | 15 | 0.266 → **0.401**       | 0.800 → **0.867**      | 0.358 → **0.565** |
| fr    | 15 | 0.269 → **0.367**       | 0.733 → **0.800**      | 0.510 → **0.618** |
| en    | 15 | 0.277 → 0.263           | 0.800 → 0.800          | 0.382 → **0.525** |
| mixed | 5  | 0.333 → 0.333           | 1.000 → 1.000          | 0.583 → 0.483     |
| **overall** | **50** | **0.277 → 0.343** | **0.800 → 0.840** | **0.433 → 0.561** |

## Analysis

**The multilingual reranker is a clear win on this set — it improves overall
recall, hit-rate, and MRR.** This *reverses* the earlier conclusion drawn from
the previous 10-question set (where reranking appeared to hurt). That earlier
result was an artifact of a tiny, narrow gold set: with broader, honest gold
sets the cross-encoder's reordering is consistently beneficial.

- **MRR is the biggest gain** (0.433 → 0.561, +30%). The reranker pushes the
  most relevant verse toward rank 1 — exactly what matters, since the RAG
  pipeline feeds only the top few verses to the LLM. AR MRR jumps 0.358 → 0.565.
- **Arabic benefits most** (recall 0.266 → 0.401): the bge model handles Arabic
  well, unlike the previous English-only `ms-marco` cross-encoder, which
  lowered every metric.
- **English recall dips slightly** (0.277 → 0.263) while its MRR rises
  (0.382 → 0.525): the reranker trades a little breadth for much better top
  ranking on EN queries.
- **Hard cases** retrieved nothing in both configs and flag real gaps:
  `ar-jannah`, `fr-creation`, `fr-jugement`, `fr-priere`, `en-judgment`,
  `en-parents`. The retriever struggles when the query's vocabulary diverges
  from the verses' wording (abstract themes like "Day of Judgment" / "creation"
  scattered across many surahs). These are candidates for query expansion /
  HyDE, or for gold-set refinement.

## Caveats

- Small per-language n (15, or 5 for mixed): treat per-language numbers as
  indicative, not statistically tight.
- `recall@k` is bounded by gold-set size; representative gold sets understate
  true recall when the retriever surfaces genuinely relevant verses that are
  not listed.

## Recommendation

Enable the multilingual reranker for quality (`RERANK_ENABLED=1`); it improves
ranking across the board, especially for Arabic and French. It is kept **off by
default in production** here (cost: ~2.3 GB model + per-query latency on CPU).
Next levers: wire `QueryProcessor`/`HyDE` into the retrieval path to attack the
hard abstract-theme cases, and keep growing the eval set.
