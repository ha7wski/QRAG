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
   in llama.cpp since PR #19488 (2026-02-19); the GGUF matched the published artifact's byte
   size (5 104 022 560 bytes) — a size check, not an integrity check, which is why the
   migration now identifies the artifact by sha256 (Decision 8).

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
*"DECIDED ON MEASURED OUTPUT: qwen2.5:7b does not hold the register."* That verdict is taken
as settled. Jais is Arabic-first; the migration is **immediate** and is not gated on a second
register measurement.

## Goals / Non-Goals

**Goals:**
- Make Jais 2 8B the default local model behind `LLM_PROVIDER=ollama`, in one commit that
  moves `.env`, code defaults, launcher fallbacks, test pins and runbook together.
- Pin the chat template explicitly so the model is never mis-prompted silently.
- State the memory budget as a precondition, and make a Metal OOM a recognised failure mode
  rather than a mystery.
- Keep the API's provenance tags (`synthesis_source`, `model_id`) truthful automatically.
- Close the gold-set hole: a frozen recording must not outlive the model that produced it,
  and a superseded recording is kept under its model id rather than overwritten.
- Write down the configuration actually shipped (quant, `num_ctx`, keep-alive, sha256), so the
  next person knows what runs.
- Make `scripts/run.sh` refuse to be quiet about serving a local model from Docker on macOS.

**Non-Goals:**
- Re-measuring the Tahlil register, or comparing Jais against qwen. qwen's verdict stands; a
  later comparison stays possible because the qwen recording is preserved (Decision 7), but it
  is not part of this change.
- Changing retrieval. Embeddings, reranking, Qdrant and BM25 are untouched.
- Rewriting `tahlil/prompts.py` for Jais. The prompts encode observed qwen failure modes;
  whether Jais needs different prompts is a question for a later change, not an assumption
  this one acts on.
- Editing the historical records that name qwen (see Decision 6).
- Adding an Anthropic fallback or a third provider.
- Enabling the `madar` LLM synthesis or restoring `lisan`'s removed synthesis step. Those
  were disabled on measured grounds and stay disabled until separately re-measured.

## Decisions

### 1. Quantization: Q4_K_M, with Q3_K_M as the documented fallback

Q4_K_M (5.10 GB) matches qwen2.5:7b's quantization level, so the swap changes the model and
not the precision class, and it is one of the quants the upstream PR lists as tested. If the resident budget
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

### 5. One commit: `.env` and every repetition of the model name move together

There is no interim env-only phase. `.env`, `.env.example`, `DEFAULT_OLLAMA_MODEL`, the
launcher fallbacks, the two API defaults, the four test pins, the gold assertion with its
re-frozen recording, and the runbook land in the **same commit**. With no comparison to wait
for, a window in which `.env` says Jais while the code, tests and runbook still say qwen would
only be a window in which the repository contradicts itself.

The one check an env-first order used to give — a mis-loaded `.env` masked by a code default
that already agrees — is kept by verifying the switch before the defaults are rewritten in the
working tree: `/health` and `model_id_from_env()` must report Jais with `.env` alone set.

*Rollback* is a revert of that single commit (qwen stays installed for one cycle).

`_synthesis_source()` and `model_id_from_env()` need no change at all — they already read the
live provider and model, so the audit tags follow the switch on their own.

### 6. Do not rewrite the historical qwen references

`tahlil/{prompts,generator,citations}.py`, `madar/{madar_service,synthesis_prompt}.py`,
`lisan/*` and `openspec/changes/add-tahlil-analysis/*` name qwen because they record
behaviour that was *observed* — the Latin/CJK drift, the field contract that "did not land",
the two claims that passed the gate. These are the decision record, not configuration.
Editing them would falsify it. The drift guards themselves stay active: they cost nothing,
and no claim about Jais's drift is yet measured.

### 7. Assert `versions.model` in the gold replay, re-freeze, keep the qwen recording

`tests/test_tahlil_gold_replay.py` asserts `prompt`, `kb` and `letters` but not `model`. The
tier would therefore keep replaying 27 frozen qwen answers, green, while production runs
Jais. Dropping the register comparison makes this assertion **more** important, not less:
without it the suite does not mis-evaluate, it lies. Adding it makes the tier fail at the
moment of the switch — the behaviour the module's own docstring demands: *"Silently
re-baselining onto whatever the model says today is precisely what a gold set exists to
prevent."*

Then the 27 are re-frozen under Jais with the explicit recording command
(`tests/gold/record_generation.py`), which becomes `tests/gold/generated.json`. The qwen
recording is **preserved beside it, under its model id** (e.g.
`tests/gold/generated.ollama_qwen2.5_7b.json`, `versions.model` unchanged inside), never
overwritten. The replay reads only the active recording; the preserved one is inert data that
makes a later qwen/Jais comparison free if it is ever wanted.

### 8. Identify the artifact by sha256

Byte size catches a truncated download and nothing else. The GGUF is identified by its sha256:
taken from the publisher if published, otherwise **computed at import** from the file (or from
the Ollama blob, whose name is its sha256) and recorded in the runbook next to the shipped
configuration.

### 9. `scripts/run.sh` warns loudly before a Metal-less local model

The committed launcher starts Ollama in Docker. On macOS, Docker Desktop has no Metal access,
so a containerised Jais runs on CPU — far slower, and inside the VM whose memory reservation
already froze this machine once. When it is about to start a local model in Docker on
`Darwin`, the launcher SHALL print a loud, unmissable warning (or stop, unless explicitly
overridden) naming the native path. Moving `run.sh` to native Ollama is still out of scope.

### 10. The shipped configuration is written down

Whatever actually runs — quant (Q4_K_M or the Q3_K_M fallback), `num_ctx`, `OLLAMA_KEEP_ALIVE`,
Modelfile tag, artifact sha256 — is written into `CLAUDE.md` (memory-budget section) and the
runbook. If an escape hatch was needed, that is stated plainly. This is a record of what
runs, not a verdict about the model.

## Risks / Trade-offs

- **Jais does not hold the register either** → Accepted risk: the change does not measure it.
  The qwen gold recording is preserved, so a comparison can be run later at no cost; qwen stays
  installed for one cycle, so reverting the adoption commit restores it.

- **The machine cannot hold Jais alongside the stack** → Escape hatches in order: Q3_K_M,
  then `num_ctx 2048`, then a shorter `OLLAMA_KEEP_ALIVE` so the model is not resident between
  requests. If none suffice, the change stops before the switch. Whichever hatch was used is
  written into `CLAUDE.md` and the runbook as the shipped configuration.

- **A silent Metal OOM is mistaken for a model or template defect** → Recorded here and in the
  spec as a named failure mode, with the log signature to grep for
  (`kIOGPUCommandBufferCallbackErrorOutOfMemory`, `backend is in error state`). This cost
  significant investigation time once; it should cost none the next time.

- **No LLM at all during the window** → There is no `ANTHROPIC_API_KEY` configured, so qwen is
  the only rollback target. It stays installed for one cycle after the switch, at ~4.4 GB of
  disk, and is uninstalled only then.

- **Jais's own drift profile is unknown** → It is Arabic-English, so CJK drift is unlikely, but
  the existing post-checks in `madar_service.py` and `tahlil/citations.py` remain enabled. The
  one-shot Latin/CJK check during import is a **smoke test**, not a validation of the register.

- **The GGUF repo is gated** → `inception42/Jais-2-8B-Chat-GGUF` requires an authenticated
  HuggingFace account with the licence accepted (Apache-2.0). `ollama pull hf.co/…` cannot
  authenticate, so the weights must be fetched with an authenticated client and imported via a
  Modelfile. A machine without that access cannot reproduce the setup from the runbook alone.

## Migration Plan

1. **Precondition** — free memory on the target machine; the backend stopped, heavy apps closed.
2. **Acquire** — authenticated download of Q4_K_M; identify it by sha256 (published, or
   computed at import) and record it.
3. **Import** — `ollama create` from a Modelfile carrying the explicit `TEMPLATE`, the stop
   tokens, and `num_ctx 4096`. Verify with `ollama show --modelfile`.
4. **Validate offline** — Arabic and English generation on a fresh runtime; confirm no
   memory-eviction or Metal error in the log; Latin/CJK smoke test; record resident cost,
   load time and tok/s; apply escape hatches if needed.
5. **Switch and adopt (one commit)** — `.env`, `.env.example`, code defaults, launcher
   fallbacks and the `run.sh` Metal guard, the two API defaults, the four test pins, the
   `versions.model` assertion with the Jais re-freeze and the preserved qwen recording, and the
   runbook + `CLAUDE.md` stating the exact shipped configuration.
6. **Retire** — one cycle after the switch, remove qwen from Ollama and delete the source GGUF.

**Rollback:** revert the single switch commit and restart; qwen is still installed until
step 6.

## Open Questions

- **Does Jais 2 hold the تعليل register?** Not measured by this change, by decision. The
  preserved qwen recording and the re-frozen Jais one make that comparison cheap if it is ever
  run — as a separate change.
- **Does Jais need different prompts?** `tahlil/prompts.py` is shaped against qwen's failures.
  They stay as they are; if Jais shows a *different* failure mode in use, that is a separate
  change, not a patch inside this one.
- **Does the resident cost fit with the reranker loaded?** `SEARCH_RERANK_ENABLED=1` adds ~1.1 GB
  when `/search` first loads it. The measurement in step 4 should be taken both with and without
  it before Jais is called validated.
- **Should `scripts/run.sh` keep running Ollama in Docker?** It still does. This change only adds
  the loud Metal guard (Decision 9); moving the committed launcher to native Ollama is a
  separate change.
