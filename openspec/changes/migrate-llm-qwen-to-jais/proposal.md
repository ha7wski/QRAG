## Why

`qwen2.5:7b` was measured — not assumed — to fail the one job the local LLM has in this
project. `add-tahlil-analysis/tasks.md` records the verdict: *"DECIDED ON MEASURED OUTPUT:
qwen2.5:7b does not hold the register"*, which is why the Tahlil acceptance verdict is
negative. The same model forced the removal of `lisan/`'s synthesis step (it corrupted
Arabic tokens) and made `madar/`'s synthesis unreliable enough to be off by default. Three
of the project's generative surfaces are degraded or disabled because of the model, and the
prompts in `tahlil/prompts.py` are shaped around its failure modes (Latin/CJK drift) rather
than around the task.

`Jais-2-8B-Chat` (Inception, Apache-2.0) is an Arabic-English bilingual model trained
Arabic-first. It is the plausible fix for a register failure that a general multilingual
model was never going to pass, and it aligns the runtime with the project's stated scope:
studying the Quran through itself, in Arabic.

**The migration is immediate, not a comparison.** qwen has already been measured and judged
insufficient; that verdict is not re-opened, and Jais is adopted without a second register
measurement gating it. The change is done when Jais runs within the memory budget and the
repository names it everywhere qwen was the configured default — not when a verdict moves.

## What Changes

- **Swap the default local model** from `qwen2.5:7b` to a Jais 2 8B build served by Ollama,
  in **one commit**: `.env`, the code defaults, the launcher fallbacks, the test pins and the
  runbook move together. The provider abstraction in `llm_client/__init__.py` is unchanged —
  only which model it names.
- **Pin the chat template explicitly** in the Ollama Modelfile. Ollama auto-detects
  `llama3-instruct` for this GGUF, which is wrong on two counts: Jais 2's generation role is
  `ai` (not `assistant`) and its template has no newline after `<|end_header_id|>`. A model
  imported without an explicit `TEMPLATE` is mis-prompted with no error.
- **Make the memory budget a stated constraint, not an accident.** Jais 2 uses full MHA
  (26 KV heads) where qwen2.5 uses GQA (4), so its KV cache costs ~7.4× more per token.
  `num_ctx` must stay at 4096 and the resident cost (~6.4 GiB vs qwen's ~4.8 GiB) must fit
  before the model is declared working — a Metal OOM does not raise, it silently poisons the
  backend and every later response degenerates to a single repeated token.
- **Write down the configuration actually shipped.** If a memory escape hatch was needed
  (Q3_K_M, `num_ctx 2048`, a shortened `OLLAMA_KEEP_ALIVE`), the exact shipped configuration
  — quant, `num_ctx`, keep-alive, and the artifact's sha256 — goes into `CLAUDE.md` and the
  runbook. Not as a verdict: so the next person knows what runs.
- **Identify the artifact by sha256, not byte size.** Computed at import if the publisher does
  not publish one, and recorded.
- **Guard `scripts/run.sh` against a Metal-less local model.** The committed launcher runs
  Ollama in Docker, which on macOS has no Metal access; it must fail loudly (or warn loudly)
  before starting a local model that way, rather than silently serve Jais on CPU.
- **Assert model provenance in the Tahlil gold set — more important without a comparison,
  not less.** `tests/gold/generated.json` records `"model": "ollama:qwen2.5:7b"`, but
  `test_tahlil_gold_replay.py` asserts only the prompt, KB and letters versions. After the
  swap the 27 frozen qwen answers would keep replaying green while production runs Jais:
  that is not an evaluation question, it is a test suite that lies. **BREAKING** for the
  gold tier: the assertion is added, the 27 are re-frozen under Jais, and the qwen recording
  is **kept beside it under its own model id, not overwritten** — the material for a later
  comparison, at zero cost today.
- **Keep `qwen2.5:7b` installed for one cycle after the switch**, then uninstall it. There is
  no `ANTHROPIC_API_KEY` configured, so qwen is the only rollback target.

Out of scope: the retrieval stack. Embeddings (`multilingual-e5-large-instruct`) and the
reranker (`bge-reranker-v2-m3`) tokenize independently of the LLM, so no re-indexing, no
Qdrant rebuild, and no BM25 change follows from this swap.

## Capabilities

### New Capabilities
- `llm-runtime`: the contract for the local generation backend — which model backs
  `LLM_PROVIDER=ollama`, how its chat template is pinned, the memory budget it must fit
  within, the provenance tag it publishes through the API, the rule that a stored gold
  recording is bound to the model that produced it (and a superseded one is kept, not
  overwritten), and the rule that the shipped configuration is written down.

### Modified Capabilities
<!-- None. The existing specs (fassila-analysis, fassila-surah-comparison,
     qlisan-word-analysis, verse-study, root-attribution, qac-morphosyntax-index) reference
     the LLM only to assert its ABSENCE from their paths ("no LLM on the path", "invoke no
     LLM"). Swapping which model serves the generative surfaces changes no requirement they
     state. -->

## Impact

**Configuration and defaults** (the model name is repeated in six places — all change in the
same commit as `.env`):
- `.env` / `.env.example` — `OLLAMA_MODEL`
- `llm_client/__init__.py:24` — `DEFAULT_OLLAMA_MODEL`, plus the docstring at line 11
- `scripts/run.sh:69`, `local-dev/start.sh:166` — shell fallbacks; `start.sh:7,256` comments
- `api/models/madar.py:45` — `synthesis_source` field default, which reaches the frontend
- `madar/madar_service.py:215` — runtime fallback for the same audit tag

**Tests that pin the string** (all pass the model explicitly, so an env-only switch does not
break them; they must be updated in the same commit as the code defaults):
- `tests/test_madar.py:167,218`, `tests/test_tahlil_generator.py:710-711`

**Gold set**: `tests/gold/generated.json` (27 frozen answers, `versions.model`, re-frozen
under Jais), the preserved qwen recording beside it under its model id, and
`tests/test_tahlil_gold_replay.py:83`.

**Runbook and docs**: `scripts/README.md:30,34,195`, `local-dev/README.md:14,138` (the
`ollama pull` line and the "~4.7 GB" figures), and `CLAUDE.md`'s memory-budget notes — all
stating the exact shipped configuration and the artifact sha256.

**Launcher guard**: `scripts/run.sh` (Docker-hosted Ollama on macOS has no Metal).

**Deliberately untouched**: the empirical records in `tahlil/{prompts,generator,citations}.py`,
`madar/{madar_service,synthesis_prompt}.py`, `lisan/*` and `openspec/changes/add-tahlil-analysis/*`
name qwen because they document behaviour that was *observed*. Rewriting them would falsify
the decision record. Their Latin/CJK drift guards stay in place — they cost nothing and no
claim is yet measured about Jais's drift.

**No re-measurement of the register**: the Tahlil verdict in `add-tahlil-analysis/tasks.md`
is not re-run by this change. The drift checks run once as a **smoke test** (the model does not
wander into Latin/CJK), which is not a validation of the register.

**Operational**: model weights ~5.1 GB (Q4_K_M) in `~/.ollama`; the source GGUF repo
`inception42/Jais-2-8B-Chat-GGUF` is gated and needs an authenticated HuggingFace account.
Ollama and llama.cpp both carry the `jais2` architecture, so no engine change is required.
