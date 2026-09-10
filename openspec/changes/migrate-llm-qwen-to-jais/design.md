## Context

`llm_client/__init__.py` is a narrow, well-behaved seam: it exposes `chat()` and
`stream_chat()` and switches between Ollama and Anthropic on `LLM_PROVIDER`. Everything
upstream (retrieval, RRF, root resolution) hands it **text**, and the embedder and reranker
tokenize independently of it. Swapping the local model is therefore a configuration change
at the architecture level — no re-indexing, no Qdrant rebuild, no BM25 change.

The cost is not architectural, it is **operational**, and a live investigation on the target
machine (16 GB M2, Ollama 0.33.3, macOS 26.5) established three facts that shape this design:

1. **The model runs.** `Jais-2-8B-Chat` Q4_K_M loads and generates correct Arabic and English
   on both Ollama's bundled llama.cpp and upstream build 10809. Architecture `jais2` has been
   in llama.cpp since PR #19488 (2026-02-19); the GGUF was verified byte-identical to the
   published artifact (5 104 022 560 bytes).

2. **Ollama's auto-detected chat template is wrong.** On import it selects
   `llama3-instruct`. Jais 2's published `chat_template.jinja` differs on two points: the
   generation role is `ai`, not `assistant`, and there is no newline after
   `<|end_header_id|>`. Nothing warns about this.

3. **The memory budget is the binding constraint, and it fails silently.** Ollama predicted
   `6.4 GiB` for Jais at `num_ctx=4096` against `5.2 GiB` available and evicted. When Metal
   does run out, the failure is not an exception: `ggml_metal_synchronize` reports
   `kIOGPUCommandBufferCallbackErrorOutOfMemory`, the backend enters a permanent error state
   (`backend is in error state from a previous command buffer failure — recreate the backend
   to recover`), logits come back uninitialised, and **every subsequent request in that
   process returns the same token repeated** — including prompts that succeeded seconds
   earlier. The symptom mimics a tokenizer or template bug and sends the investigation the
   wrong way.

The driving reason for the change is recorded in `add-tahlil-analysis/tasks.md:695`:
*"DECIDED ON MEASURED OUTPUT: qwen2.5:7b does not hold the register."*

## Goals / Non-Goals

**Goals:**
- Make Jais 2 8B the default local model behind `LLM_PROVIDER=ollama`, reversibly.
- Pin the chat template explicitly so the model is never mis-prompted silently.
- State the memory budget as a precondition, and make a Metal OOM a recognised failure mode
  rather than a mystery.
- Keep the API's provenance tags (`synthesis_source`, `model_id`) truthful automatically.
- Close the gold-set hole: a frozen recording must not outlive the model that produced it.
- Re-run the Tahlil register measurement, which is the only thing that decides whether this
  migration was worth doing.

**Non-Goals:**
- Changing retrieval. Embeddings, reranking, Qdrant and BM25 are untouched.
- Rewriting `tahlil/prompts.py` for Jais. The prompts encode observed qwen failure modes;
  whether Jais needs different prompts is a measurement this change produces, not an
  assumption it acts on.
- Editing the historical records that name qwen (see Decision 6).
- Adding an Anthropic fallback or a third provider.
- Enabling the `madar` LLM synthesis or restoring `lisan`'s removed synthesis step. Those
  were disabled on measured grounds and stay disabled until separately re-measured.

## Decisions

### 1. Quantization: Q4_K_M, with Q3_K_M as the documented fallback

Q4_K_M (5.10 GB) matches qwen2.5:7b's quantization level, so quality is compared on equal
footing, and it is one of the quants the upstream PR lists as tested. If the resident budget
does not fit, the escape hatch is **Q3_K_M (4.18 GB, −0.9 GB)** before `num_ctx 2048`
(−0.44 GB of KV cache), because losing context hurts a RAG answer more than losing a
quantization step.

*Alternatives:* Q5_K_M / Q6_K / Q8_0 were rejected — on a machine that already fails the
budget at Q4_K_M, a larger quant is not a candidate. BF16 (16.19 GB) is out of scope.

### 2. Pin the template in the Modelfile, sourced from the published Jinja template

The Modelfile declares `TEMPLATE` and the `stop` parameters rather than trusting
auto-detection. The template is transcribed from Jais 2's `chat_template.jinja`, whose
generation prompt is `<|start_header_id|>ai<|end_header_id|>` with no trailing newline.

*Alternative rejected:* letting Ollama detect it. It picks `llama3-instruct`, which is
plausible enough to pass a casual smoke test and wrong enough to degrade every answer, with
no error to trace.

### 3. `num_ctx` stays at 4096 — the native 8192 is not an invitation

Jais 2 declares `context_length 8192`, but it uses **full MHA**: `head_count 26` and
`head_count_kv 26`, against qwen2.5's GQA with 4 KV heads. Per-token KV cost is ~0.41 MB vs
~0.055 MB — **7.4×**.

| ctx | qwen2.5:7b | Jais-2-8B |
|-----|-----------|-----------|
| 4096 | 0.23 GB | 1.74 GB |
| 8192 | 0.47 GB | 3.49 GB |

The project already runs at `OLLAMA_NUM_CTX=4096` and does not fill it, so the migration
costs nothing in context. Raising it to 8192 would add ~1.74 GB of wired Metal memory on a
machine documented in `CLAUDE.md` as having frozen hard under exactly this pressure.

### 4. Validate on a quiet machine, and treat OOM as a hard stop

Because a Metal OOM poisons the process rather than raising, validation must run with the
backend stopped and memory-heavy applications closed, and any OOM in the log invalidates
every measurement taken after it in the same process. The acceptance sequence is: check free
memory → start a fresh runtime → warm up → measure. A model that "works then stops working"
is a memory failure until proven otherwise.

### 5. Env-first migration order, code defaults last

The switch happens through `.env` alone. Code defaults, launcher fallbacks, tests and the
runbook are updated in a **single later commit**, only after the register measurement lands.
This keeps the whole migration reversible with one line for as long as the outcome is
uncertain, and prevents a mis-loaded `.env` from being masked by a code default that already
agrees with it.

`_synthesis_source()` and `model_id_from_env()` need no change at all — they already read the
live provider and model, so the audit tags follow the switch on their own.

### 6. Do not rewrite the historical qwen references

`tahlil/{prompts,generator,citations}.py`, `madar/{madar_service,synthesis_prompt}.py`,
`lisan/*` and `openspec/changes/add-tahlil-analysis/*` name qwen because they record
behaviour that was *observed* — the Latin/CJK drift, the field contract that "did not land",
the two claims that passed the gate. These are the decision record, not configuration.
Editing them would falsify it. The drift guards themselves stay active: they cost nothing,
and no claim about Jais's drift is yet measured.

### 7. Assert `versions.model` in the gold replay

`tests/test_tahlil_gold_replay.py` asserts `prompt`, `kb` and `letters` but not `model`. The
tier would therefore keep replaying 27 frozen qwen answers, green, while production runs
Jais. Adding the assertion makes the suite fail at the moment of the switch — which is the
behaviour the module's own docstring demands: *"Silently re-baselining onto whatever the
model says today is precisely what a gold set exists to prevent."*

## Risks / Trade-offs

- **Jais does not hold the register either** → The gold-set measurement is the decision point,
  not the model swap. If the verdict stays negative, `.env` reverts in one line and the change
  is archived with the measurement recorded — a negative result that cost no code.

- **The machine cannot hold Jais alongside the stack** → Escape hatches in order: Q3_K_M,
  then `num_ctx 2048`, then a shorter `OLLAMA_KEEP_ALIVE` so the model is not resident between
  requests. If none suffice, the change stops at "measured, not adopted".

- **A silent Metal OOM is mistaken for a model or template defect** → Recorded here and in the
  spec as a named failure mode, with the log signature to grep for
  (`kIOGPUCommandBufferCallbackErrorOutOfMemory`, `backend is in error state`). This cost
  significant investigation time once; it should cost none the next time.

- **No LLM at all during the window** → There is no `ANTHROPIC_API_KEY` configured, so removing
  qwen before validation would leave the stack without a provider. qwen stays installed until
  the register verdict is recorded (spec requirement), at ~4.4 GB of disk.

- **Jais's own drift profile is unknown** → It is Arabic-English, so CJK drift is unlikely, but
  the existing post-checks in `madar_service.py` and `tahlil/citations.py` remain enabled. They
  are cheap and a false sense of safety is the more expensive error.

- **The GGUF repo is gated** → `inception42/Jais-2-8B-Chat-GGUF` requires an authenticated
  HuggingFace account with the licence accepted (Apache-2.0). `ollama pull hf.co/…` cannot
  authenticate, so the weights must be fetched with an authenticated client and imported via a
  Modelfile. A machine without that access cannot reproduce the setup from the runbook alone.

## Migration Plan

1. **Precondition** — free memory on the target machine; the backend stopped, heavy apps closed.
2. **Acquire** — authenticated download of Q4_K_M, verified against the published byte size.
3. **Import** — `ollama create` from a Modelfile carrying the explicit `TEMPLATE`, the stop
   tokens, and `num_ctx 4096`. Verify with `ollama show --modelfile`.
4. **Validate offline** — Arabic and English generation on a fresh runtime; confirm no
   memory-eviction or Metal error in the log; record resident cost, load time and tok/s.
5. **Switch** — `OLLAMA_MODEL` in `.env` only. Restart. Confirm `/health` reports `llm: true`.
6. **Measure** — re-run the Tahlil register measurement on the gold set under Jais; record the
   verdict and the model it was measured on.
7. **Adopt (only if the verdict is positive)** — one commit updating code defaults, launcher
   fallbacks, the two API defaults, the four test pins, the runbook, and adding the
   `versions.model` assertion plus the re-frozen recording.
8. **Retire** — remove qwen from Ollama and delete the source GGUF, one cycle after adoption.

**Rollback:** at any point before step 7, restore `OLLAMA_MODEL` in `.env` and restart. After
step 7, revert the single adoption commit; qwen is still installed until step 8.

## Open Questions

- **Does Jais 2 hold the تعليل register?** Undecidable before step 6. It is the whole point of
  the change and is deliberately not pre-judged here.
- **Does Jais need different prompts?** `tahlil/prompts.py` is shaped against qwen's failures.
  If Jais passes the register bar with the existing prompts, they stay; if it fails in a
  *different* way, that is a separate change, not a patch inside this one.
- **Does the resident cost fit with the reranker loaded?** `SEARCH_RERANK_ENABLED=1` adds ~1.1 GB
  when `/search` first loads it. The measurement in step 4 should be taken both with and without
  it before Jais is called validated.
- **Should `scripts/run.sh` keep running Ollama in Docker?** It still does, and Docker Desktop on
  macOS has no Metal access — a containerised Jais would be far slower and heavier than the
  native path `local-dev/start.sh` uses. Out of scope here, but the runbook update in step 7
  will make the discrepancy more visible.
