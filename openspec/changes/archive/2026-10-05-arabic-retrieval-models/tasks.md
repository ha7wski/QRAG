## 0. Phase 0 — audit (done 2026-10-05)

- [x] 0.1 Read `indexing/embedder.py`, `retrieval/reranker.py`, `retrieval/root_channel.py`, `api/routers/search.py`, `indexing/hybrid_search.py`, `retrieval/similar_verses.py`, `.env`
- [x] 0.2 Locate the Arabic gold sets (`phrase_qa` 27, `qa_dataset` 40, `root_concordance_qa` 30)
- [x] 0.3 Check for an Arabic tafsir on disk (none)
- [x] 0.4 Verify every candidate id on the Hub (public, ungated, safetensors, licence) and read each card's prompt format

## 1. Gate — user validation before any code

- [x] 1.1 User accepts or amends the adoption rule (design D4), the candidate list (D1), the instruction `T` and the pool strategies (D5) — frozen from here on
- [x] 1.2 User answers the tafsir question (Open Question 1): no tafsir — variant (b) is out

## 2. Phase 1 — benchmark (local-only, no production impact)

- [x] 2.1 `tests/eval/bench_arabic_retrieval.py`: preflight (backend port and Ollama loaded-model check), gold loading, metrics (Recall@5/10, MRR@10, nDCG@10, Hit@10), paired bootstrap — unit-check the metrics on a hand-made ranking
- [x] 2.2 Encoder adapters per D1 (prefix/instruct/padding table), D2 variants a1/a2 + E5-deployed text, cached `.npy` vectors keyed by model revision, one model resident at a time with MPS cleanup
- [x] 2.3 Config A (dense alone, brute-force cosine) on the three gold sets
- [x] 2.4 Reranker adapters: `CrossEncoder` for BERT rerankers, yes/no head for `Qwen3-Reranker-0.6B` per its card
- [x] 2.5 Config B through the real `api.routers.search.search` with a stand-in `app.state`; confirm the baseline reproduces `search_eval.py`'s live numbers
- [x] 2.6 Config C (C1 append / cap 48, C2 RRF-order / cap 32) with the `N_DENSE = 0` parity assertion against B
- [x] 2.7 Arabic-only BM25 measured inside config B (built in memory, not saved under `data/`)
- [x] 2.8 ~~Report-only chat-hybrid RRF~~ — dropped: the chat path is a separate change (user, 2026-10-05)
- [x] 2.9 Run (backend + Ollama stopped); write `eval/arabic_retrieval/report.md` + `results.json`; verdicts per D4

Run notes (2026-10-05): first run aborted by hand when the Qwen3-Reranker worker reached
17 GB (full `[batch, seq, 151k]` logits on MPS, swap 13/14 GB); fixed with
`logits_to_keep=1` (scores checked identical, max diff 0.0), batch 8, a 6 GB MPS ceiling per
worker; only that reranker was re-run. Results: `eval/arabic_retrieval/report.md`.

## 3. Gate — user reads the table

- [x] 3.1 User validates: Phase 2 limited to C-rrf, shared E5 singleton, collection reusable by the chat fix, old path kept, flag off by default (2026-10-05)

## 4. Phase 2 — the C-rrf channel (design D8)

- [x] 4.1 `indexing/embedder_ar.py`: instruction, passage/query formatting, format tag — no model
- [x] 4.2 `indexing/build_index_ar.py`: same ids/payload/indexes as `quran_verses` + `emb_model`/`emb_format`; refuses a name equal to `QDRANT_COLLECTION` and a non-E5 embedder; build it (backend stopped)
- [x] 4.3 `retrieval/dense_ar_channel.py` over the shared embedder and Qdrant client; abstains on missing collection or model mismatch
- [x] 4.4 `api/routers/search.py` RRF pool when the channel returns ids; `api/main.py` wires `app.state.search_dense_ar` only under `SEARCH_DENSE_AR_ENABLED=1`
- [x] 4.5 `.env.example` documents the three variables
- [x] 4.6 Tests: flag-off / empty-channel route identical to today; RRF pool order; filters reach Qdrant; abstention; name refusal; repo-shape tests still pass
- [x] 4.7 Parity: route with the flag reproduces the bench's C-rrf ids on the 97 gold queries
- [x] 4.8 Resident memory of the backend, flag on vs off, after a `/search`

Phase 2 results (2026-10-05, `eval/arabic_retrieval/`):
- `quran_verses` fingerprint (6 236 points, ids + payloads + vectors) identical before and after the build.
- Parity: 89/97 final rankings identical to the bench's C-rrf. The 8 others differ on near-ties: MPS
  leaves E5 norms at 1 ± 3e-4 and Qdrant renormalizes stored vectors, so production ranks by true
  cosine where the bench carried a per-verse norm bias. Measured on the production path the rule
  still holds: union nDCG@10 +0.029, CI [+0.005, +0.056], phrase Hit@10 unchanged (0.963).
- Resident memory (top MEM, incl. wired MPS) after `/search`: flag off 4 556 MB, flag on 6 181 MB
  (+1 625 MB = the one shared E5). Flag-off live numbers equal the pre-change baseline.

## 5. Phase 3 — not run

- [x] 5.1 Conditional on a reranker win (D-rr): none won, so no similarity rebuild
