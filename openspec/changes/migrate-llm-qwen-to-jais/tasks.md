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
- [ ] 1.2 Record the baseline: current `OLLAMA_MODEL`, and qwen's resident cost and tok/s on
      the same prompt used later for Jais, so the comparison is like-for-like.
- [ ] 1.3 Free the machine: stop the backend (`./local-dev/stop.sh`), close memory-heavy
      applications, and confirm at least 7 GB of unused physical memory.
- [ ] 1.4 Confirm at least 12 GB free disk before any download.

## 2. Acquire and import the model

- [ ] 2.1 If the Ollama blob is absent, download Q4_K_M with an authenticated client and verify
      the file is exactly 5 104 022 560 bytes.
- [ ] 2.2 Write the Modelfile with an explicit `TEMPLATE` transcribed from Jais 2's published
      `chat_template.jinja`: generation role `ai`, no newline after `<|end_header_id|>`.
- [ ] 2.3 Declare `PARAMETER stop` for `<|eot_id|>` and `<|start_header_id|>`, and
      `PARAMETER num_ctx 4096` matching `.env`.
- [ ] 2.4 `ollama create` the model and verify with `ollama show --modelfile` that the
      `TEMPLATE` block is non-empty and its generation role is `ai`, not `assistant`.
- [ ] 2.5 Verify `ollama show` reports `architecture jais2` and `quantization Q4_K_M`.

## 3. Validate the model offline

- [ ] 3.1 Start a fresh Ollama runtime, send one warm-up request, then generate on an Arabic
      Quranic prompt and confirm the answer is fluent, on-topic and ends at a turn boundary.
- [ ] 3.2 Grep the runtime log for `kIOGPUCommandBufferCallbackErrorOutOfMemory`,
      `backend is in error state` and `exceed available memory`. Any hit invalidates every
      measurement taken after it in that process — restart and redo 3.1.
- [ ] 3.3 Run the drift post-checks the project already enforces: assert the Arabic output
      contains no Latin word-characters and no CJK, matching `madar_service.py` and
      `tahlil/citations.py`.
- [ ] 3.4 Record resident cost (`ollama ps`), cold load time and tok/s; compare against the
      qwen baseline from 1.2.
- [ ] 3.5 Repeat 3.1 and 3.4 with `SEARCH_RERANK_ENABLED=1` and the reranker loaded, to check
      the budget holds with the ~1.1 GB cross-encoder resident (design §Open Questions).
- [ ] 3.6 If the budget does not hold, apply the escape hatches in order — Q3_K_M, then
      `num_ctx 2048`, then a shorter `OLLAMA_KEEP_ALIVE` — re-running 3.1–3.4 after each, and
      record which one was needed.

## 4. Switch the application (configuration only, fully reversible)

- [ ] 4.1 Back up `.env`, then set `OLLAMA_MODEL` to the validated Jais tag. Change nothing else.
- [ ] 4.2 Restart the stack and confirm `GET /health` reports `llm: true` and
      `models: {embedder: false, search_reranker: false}` — the lazy-loading invariant must
      still hold.
- [ ] 4.3 Exercise `POST /chat/stream` end-to-end and confirm streamed Arabic renders correctly
      in the frontend, RTL included.
- [ ] 4.4 Confirm `synthesis_source` in a `madar` response now reports the Jais tag with the
      `-local` suffix, with no code change (`_synthesis_source()` reads the live client).
- [ ] 4.5 Confirm `model_id_from_env()` returns `ollama:<jais tag>` while the Ollama server is
      stopped, so cache and review keys stay resolvable during an outage.
- [ ] 4.6 Verify rollback: restore the backed-up `.env`, restart, confirm qwen serves again.
      Then switch back to Jais.

## 5. Re-measure the register decision

- [ ] 5.1 Re-run the Tahlil acceptance measurement on the gold set under Jais, using the same
      criteria that produced the negative verdict for qwen.
- [ ] 5.2 Record the verdict in `add-tahlil-analysis/tasks.md` naming the model it was measured
      on, alongside the existing qwen verdict rather than replacing it.
- [ ] 5.3 **Decision gate.** If the verdict is negative, stop: revert `.env` to qwen, archive
      this change with the measurement recorded, and do not proceed to §6.

## 6. Adopt (single commit, only if 5.3 is positive)

- [ ] 6.1 Update `llm_client/__init__.py:24` `DEFAULT_OLLAMA_MODEL` and the docstring at
      line 11.
- [ ] 6.2 Update the launcher fallbacks: `scripts/run.sh:69`, `local-dev/start.sh:166`, and the
      comments at `local-dev/start.sh:7,256` including the "~4.7 GB" figure.
- [ ] 6.3 Update the two API defaults: `api/models/madar.py:45` `synthesis_source` and
      `madar/madar_service.py:215`.
- [ ] 6.4 Update `.env.example:4` and the runbook: `scripts/README.md:30,34,195` and
      `local-dev/README.md:14,138`.
- [ ] 6.5 Update the four test pins: `tests/test_madar.py:167,218` and
      `tests/test_tahlil_generator.py:710-711`.
- [ ] 6.6 Add the gold-set guard: assert `versions["model"] == G.model_id_from_env()` in
      `tests/test_tahlil_gold_replay.py`, and confirm it fails against the qwen recording.
- [ ] 6.7 Re-freeze the gold recording under Jais with the explicit recording command, then
      confirm 6.6 passes and the 27 replayed answers still exercise the full chain.
- [ ] 6.8 Run the full suite and confirm no regression beyond the pre-existing
      `test_service_synthesis_disabled_by_default` failure, which is unrelated to this change.
- [ ] 6.9 Leave the historical qwen references untouched — `tahlil/{prompts,generator,citations}.py`,
      `madar/{madar_service,synthesis_prompt}.py`, `lisan/*`,
      `openspec/changes/add-tahlil-analysis/*` — and confirm the Latin/CJK drift guards are
      still enabled.

## 7. Retire the outgoing model

- [ ] 7.1 After one cycle of use on Jais, remove `qwen2.5:7b` from Ollama.
- [ ] 7.2 Delete the redundant source GGUF and the intermediate `jais2:8b-q4km` tag if the
      correctly-templated model carries a different name.
- [ ] 7.3 Update `CLAUDE.md` so the documented default model and the memory-budget notes match
      what the project actually runs.
