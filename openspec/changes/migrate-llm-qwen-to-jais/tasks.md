> **State already on disk before this plan is applied.** A live investigation on the target
> machine already downloaded `Jais-2-8B-Chat` Q4_K_M and imported it into Ollama twice:
> `jais2:8b-q4km` (auto-detected `llama3-instruct` template — **wrong**, see design §2) and
> `jais2:8b` (explicit `TEMPLATE` with the `ai` generation role — correct). `qwen2.5:7b` is
> still installed and `.env` is unmodified, so the app runs exactly as before. The source GGUF
> was deleted after import; the Ollama blob is the surviving copy, so §2 rebuilds from
> `FROM jais2:8b-q4km` rather than from a file. **No generation has yet been validated on a
> machine with enough free memory** — every attempt so far ran into the Metal OOM described in
> design §Context, so §3 is the first task that produces a trustworthy measurement.

## 1. Preconditions

- [ ] 1.1 Confirm HuggingFace access: `hf auth whoami` succeeds and a `HEAD` on
      `inception42/Jais-2-8B-Chat-GGUF/resolve/main/Q4_K_M.gguf` returns `302`, not `401`.
- [ ] 1.2 Record the current `OLLAMA_MODEL` (for rollback), and qwen's resident cost and
      tok/s on the prompt used later for Jais — as the operational reference for the budget,
      not as a quality comparison.
- [ ] 1.3 Free the machine: stop the backend (`./local-dev/stop.sh`), close memory-heavy
      applications, and confirm at least 7 GB of unused physical memory.
- [ ] 1.4 Confirm at least 12 GB free disk before any download.

## 2. Acquire and import the model

- [ ] 2.1 If the Ollama blob is absent, download Q4_K_M with an authenticated client.
- [ ] 2.2 Identify the artifact by **sha256**, not byte size: use the publisher's sha256 if
      published and verify against it; otherwise compute it at import (from the file, or read
      it from the Ollama blob name) and record it for §5.
- [ ] 2.3 Write the Modelfile with an explicit `TEMPLATE` transcribed from Jais 2's published
      `chat_template.jinja`: generation role `ai`, no newline after `<|end_header_id|>`.
- [ ] 2.4 Declare `PARAMETER stop` for `<|eot_id|>` and `<|start_header_id|>`, and
      `PARAMETER num_ctx 4096` matching `.env`.
- [ ] 2.5 `ollama create` the model and verify with `ollama show --modelfile` that the
      `TEMPLATE` block is non-empty and its generation role is `ai`, not `assistant`.
- [ ] 2.6 Verify `ollama show` reports `architecture jais2` and `quantization Q4_K_M`.

## 3. Validate the model offline

- [ ] 3.1 Start a fresh Ollama runtime, send one warm-up request, then generate on an Arabic
      Quranic prompt and confirm the answer is fluent, on-topic and ends at a turn boundary.
- [ ] 3.2 Grep the runtime log for `kIOGPUCommandBufferCallbackErrorOutOfMemory`,
      `backend is in error state` and `exceed available memory`. Any hit is a **hard stop**:
      it invalidates every measurement taken after it in that process — restart and redo 3.1.
- [ ] 3.3 **Latin/CJK drift smoke test** (not a register validation): assert the Arabic output
      contains no Latin word-characters and no CJK, matching the post-checks in
      `madar_service.py` and `tahlil/citations.py`.
- [ ] 3.4 Record resident cost (`ollama ps`), cold load time and tok/s.
- [ ] 3.5 Repeat 3.1 and 3.4 with `SEARCH_RERANK_ENABLED=1` and the reranker loaded, to check
      the budget holds with the ~1.1 GB cross-encoder resident (design §Open Questions).
- [ ] 3.6 If the budget does not hold, apply the escape hatches in order — Q3_K_M, then
      `num_ctx 2048`, then a shorter `OLLAMA_KEEP_ALIVE` — re-running 3.1–3.4 after each, and
      record which one was needed (it is written down in 5.6). If none suffice, stop here.

## 4. Verify the switch before rewriting the defaults

- [ ] 4.1 Back up `.env`, then set `OLLAMA_MODEL` to the validated Jais tag (and the escape-hatch
      values from 3.6, if any), with the code defaults still naming qwen — so a mis-loaded
      `.env` cannot be masked by a default that already agrees.
- [ ] 4.2 Restart the stack and confirm `GET /health` reports `llm: true` and
      `models: {embedder: false, search_reranker: false}` — the lazy-loading invariant must
      still hold.
- [ ] 4.3 Exercise `POST /chat/stream` end-to-end and confirm streamed Arabic renders correctly
      in the frontend, RTL included.
- [ ] 4.4 Confirm `synthesis_source` in a `madar` response reports the Jais tag with the
      `-local` suffix, with no code change (`_synthesis_source()` reads the live client).
- [ ] 4.5 Confirm `model_id_from_env()` returns `ollama:<jais tag>` while the Ollama server is
      stopped, so cache and review keys stay resolvable during an outage.

## 5. Switch (single commit: `.env` + defaults + tests + runbook)

Everything in this section lands in **one commit** together with the `.env` change from 4.1.

- [ ] 5.1 Update `llm_client/__init__.py:24` `DEFAULT_OLLAMA_MODEL` and the docstring at
      line 11.
- [ ] 5.2 Update the launcher fallbacks: `scripts/run.sh:69`, `local-dev/start.sh:166`, and the
      comments at `local-dev/start.sh:7,256` including the "~4.7 GB" figure.
- [ ] 5.3 Add the Metal guard to `scripts/run.sh`: on `Darwin`, before starting or using
      Ollama in Docker for the local model, print a loud warning (or stop unless explicitly
      overridden) that the model will run without Metal, naming the native path.
- [ ] 5.4 Update the two API defaults: `api/models/madar.py:45` `synthesis_source` and
      `madar/madar_service.py:215`.
- [ ] 5.5 Update the four test pins: `tests/test_madar.py:167,218` and
      `tests/test_tahlil_generator.py:710-711`.
- [ ] 5.6 Write down the shipped configuration in `.env.example:4`, the runbook
      (`scripts/README.md:30,34,195`, `local-dev/README.md:14,138`) and `CLAUDE.md`'s
      memory-budget notes: model tag, quantization, `num_ctx`, `OLLAMA_KEEP_ALIVE`, artifact
      sha256 (from 2.2), and — if 3.6 applied one — the escape hatch, stated as such.
- [ ] 5.7 Add the gold-set guard: assert `versions["model"] == G.model_id_from_env()` in
      `tests/test_tahlil_gold_replay.py`, with a message naming both models, and confirm it
      fails against the qwen recording.
- [ ] 5.8 Preserve the qwen recording: copy `tests/gold/generated.json` to a file named by its
      model id (e.g. `tests/gold/generated.ollama_qwen2.5_7b.json`), `versions.model`
      unchanged. It is kept, never overwritten, and the replay does not read it.
- [ ] 5.9 Re-freeze the 27 under Jais with `python3 tests/gold/record_generation.py` into
      `tests/gold/generated.json`, then confirm 5.7 passes and the replayed answers still
      exercise the full chain. Confirm the preserved qwen file is byte-identical to before.
- [ ] 5.10 Run the full suite and confirm no regression beyond the pre-existing
      `test_service_synthesis_disabled_by_default` failure, which is unrelated to this change.
- [ ] 5.11 Leave the historical qwen references untouched — `tahlil/{prompts,generator,citations}.py`,
      `madar/{madar_service,synthesis_prompt}.py`, `lisan/*`,
      `openspec/changes/add-tahlil-analysis/*` — and confirm the Latin/CJK drift guards are
      still enabled.

## 6. Retire the outgoing model

- [ ] 6.1 After one cycle of use on Jais, remove `qwen2.5:7b` from Ollama (rollback until then
      is a revert of the §5 commit).
- [ ] 6.2 Delete the redundant source GGUF and the intermediate `jais2:8b-q4km` tag if the
      correctly-templated model carries a different name.
