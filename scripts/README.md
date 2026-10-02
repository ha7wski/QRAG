# Running Quran RAG

Operational guide: prerequisites, one-time setup, and launching the app from a
fresh clone. For the project overview (features, architecture, retrieval design)
see the top-level [`README.md`](../README.md). **Run all commands from the repo
root.**

## Prerequisites

- Python 3.11+
- Docker + Docker Compose (for Qdrant and Ollama)
- Node.js 18+ (for the frontend)

## What ships vs. what's generated

`data/` is organized by what a file **is**, and that is also the ship/build rule:

| Bucket | Holds | Committed? |
|--------|-------|-----------|
| `data/source/` | Third-party originals the project never rewrites — `quran.csv`, `quran_chakl.csv`, the QAC morphology, the treebank | yes (except `source/maqayis/`, see below) |
| `data/references/` | Curated scholarship, each file carrying a human decision | yes |
| `data/derived/` | Anything a script can rebuild: the processed corpus, the QAC indexes, the fetched translations, the BM25 index | **no — built locally** |
| `data/runtime/` | Mutable state the running app owns: the SQLite store, the embedded Qdrant collection | **no** |

So the one-time build below is required after cloning: it fills `data/derived/`
and populates Qdrant. `data/source/maqayis/` is the single documented departure
— a large re-downloadable original that is git-ignored while its curated
derivative `data/references/maqayis_asl.csv` ships.

**Every dataset's provenance lives in `quran_data/manifest.py`** — what it is,
where it came from (upstream project + URL, or the fetching script), which step
writes it, who reads it, whether it is regenerable and with which exact command.
Consult it there rather than re-deriving it from this page; it is also what the
loaders read to tell you what to run when a file is missing.

## One-time setup

```bash
# 1. Python env (.venv) + install deps + create .env from .env.example
./scripts/setup.sh && source .venv/bin/activate

# 2. Edit .env for a HOST run (the example targets Docker hostnames):
#      QDRANT_PATH=data/runtime/qdrant   # run Qdrant embedded — no container at all
#      QDRANT_URL=http://localhost:6333  # only if you leave QDRANT_PATH empty
#      OLLAMA_BASE_URL=http://localhost:11434
#      OLLAMA_MODEL=qwen2.5:7b        # or LLM_PROVIDER=anthropic + ANTHROPIC_API_KEY

# 3. Start Ollama, then pull the LLM weights (~4.7 GB)
./scripts/start_dev.sh                  # Ollama only; Qdrant runs embedded
docker exec quran-ollama ollama pull qwen2.5:7b

# 4. Build the data + indexes (translations → pipeline → embeddings)
python scripts/fetch_translations.py    # FR/EN; skip → Arabic-only retrieval
python ingestion/run_pipeline.py        # data/source/quran.csv → data/derived/
python indexing/build_index.py          # embeds into Qdrant + BM25 (first run slow)
```

## Launch (one command)

```bash
./scripts/run.sh
```

Starts Ollama (Docker), the backend (`:8000`) and the frontend (`:3000`), waits
until both are ready, and opens the browser. It brings up the Qdrant container
only when `QDRANT_PATH` is empty — with it set, Qdrant runs embedded in the
backend and there is nothing to start. It refuses to start if the indexes aren't
built (and prints the build commands). Ctrl+C stops
the app; Docker keeps running. Override ports with
`BACKEND_PORT=8001 FRONTEND_PORT=3001 ./scripts/run.sh`.

---

## Run each component yourself

Useful for development or to understand each layer.

### Ingestion pipeline

```bash
python ingestion/run_pipeline.py    # or ./scripts/ingest.sh
# Expected: "6236 verses processed, 0 errors, morphology.json created with N roots"
```

Outputs land in `data/derived/`. The ones the runtime actually loads:

| File | Description |
|------|-------------|
| `verses_final.json`    | **The serving corpus** — verses with the `roots` field filled; the backend and the indexer both load it |
| `morphology.json`      | Arabic root → forms / verses / count; powers lexical search and Verse Study |
| `qac_resolution.json`  | `form_to_roots` + `lem_to_roots` — resolves a typed word to its root(s) |
| `verses_raw.json`, `verses_enriched.json` | Stage snapshots, same schema as `verses_final`; nothing reads them |

The QLisan / Tahlīl stages write several more (`qac_words.json`,
`qac_syntax.json`, `root_graph.json`, `word_index.json`, `lemma_index.json`,
`proper_nouns.json`, `roots_resolved.json`). Rather than list them twice, see
`quran_data/manifest.py` — one entry per dataset, with its producer, its
consumers, and its rebuild command.

> **Roots come from the Quranic Arabic Corpus**, not from a stemmer:
> `data/source/quran-morphology.txt` ships manually-verified roots in native
> Arabic. `camel-tools` is therefore **not** a dependency (it is ~2 GB), and the
> legacy `tashaphyne` stemmer in `ingestion/morphology.py` is left in place but
> unused — an optional fallback behind `QAC_STEMMER_FALLBACK=1`, off by default
> because it mis-roots (`كريم` → `ريم` instead of `كرم`).

### Build the indexes

```bash
python indexing/build_index.py            # resumable via a checkpoint
python indexing/build_index.py --rebuild  # recreate the Qdrant collection
```

Embeds every verse (`intfloat/multilingual-e5-large-instruct`, 1024-dim, cosine)
into Qdrant and builds the BM25 sparse index. The first run downloads the
embedding model and can take 10–30 minutes depending on hardware.

### Build the intra-surah similarity («داخل سورة»)

```bash
python scripts/build_surah_similarity.py --dry-run        # syntax gate only: no Qdrant, no model, ~10 s
python scripts/build_surah_similarity.py                  # full build, resumes per surah
python scripts/build_surah_similarity.py --surahs 55,108  # checkpoint a few surahs (dev)
python scripts/build_surah_similarity.py --fresh          # ignore existing checkpoints
python scripts/eval_surah_similarity.py                   # measure it against the gold set
```

Writes `data/derived/surah_similarity.json`, the static lookup behind
`GET /surah/{number}/similar`: for every verse, at most 10 verses of the SAME
surah that pass both a syntactic gate (QAC word signatures) and a semantic gate
(`bge-reranker-v2-m3` + the E5 vectors + tool-filtered root coverage), and the
surah's groups of mutually close verses. Consecutive verses are never stored.
**Stop the backend first**: the build reads the verse vectors out of the
embedded Qdrant, which holds an exclusive lock — the script checks that lock and
refuses to start while it is held. It also loads the ~1.1 GB cross-encoder for
the run; nothing stays resident at serve time. Per-surah checkpoints live in
`data/derived/.surah_similarity_checkpoint/` and are reused only when the build
parameters, the derived inputs, the verse vectors and the builder's own source
all match (a torn or stale checkpoint is rebuilt); after changing code the
builder imports from elsewhere, pass `--fresh`. The final file is written once
all 114 surahs are done.

The header records the sha256 of the gold set the parameters were frozen
against (`tests/eval/surah_similarity_gold.json`, local-only). Without that file
the build refuses unless given `--no-gold` — so on a fresh clone of the repo,
which has no `tests/`, run `python scripts/build_surah_similarity.py --no-gold`
(header `gold_sha256: null`) — and `eval_surah_similarity.py`
refuses to report against a gold file whose digest differs from the header.

### Smoke-test hybrid search

```bash
python -c "from indexing.hybrid_search import HybridSearch; \
print(HybridSearch().search('الرحمن الرحيم', top_k=5))"
```

### Run the chat pipeline (CLI)

```bash
python generation/chat_engine.py "What does the Quran say about patience?"
```

> The Ollama model needs ~5–6 GB RAM. Run Ollama **natively**, not in Docker:
> Docker on macOS has no access to the Metal GPU, so a containerized model runs
> on CPU (~2 tok/s) *and* forces you to hand that memory to the Docker VM. Keep
> `OLLAMA_BASE_URL=http://localhost:11434`, or set `LLM_PROVIDER=anthropic` to
> use the Claude API and load nothing locally.
>
> **Do not raise Docker Desktop's memory limit to fit the model** — that is the
> opposite of what you want. Whatever you give the VM is taken from the host,
> where the native model and the embedders actually live. Qdrant is the only
> container here and it serves ~24 MB of vectors: 4 GB is already generous, and
> `QDRANT_PATH` removes the VM from the picture entirely (see Gotchas).

### Run the API

```bash
uvicorn api.main:app --host 127.0.0.1 --port 8000   # pick another port if 8000 is taken
```

This is the whole served surface — every route below has a caller in the
frontend, and nothing else is mounted:

| Method | Path           | Description |
|--------|----------------|-------------|
| GET    | `/health`      | Readiness: `{status, qdrant, llm, models, qdrant_location}` |
| GET    | `/search`      | Similar-verse search: `?q=...&surah=&period=&juz=&limit=` |
| POST   | `/chat/stream` | Token stream as Server-Sent Events; persists the turn under `session_id` |
| POST   | `/lisan/analyze` | Letter-level reading of a word's root: `{word}` → letters + composed Arabic reading (no LLM) |
| POST   | `/verse-lookup` | Every verse containing a word or a derivative of its root, vocalized, with match offsets |
| POST   | `/qlisan/word` | The deterministic four-level fiche for one word, by `surah:ayah:word` |
| GET    | `/qlisan/verse/{surah}/{ayah}` | Vocalized verse + QAC-aligned token boundaries, for word selection |
| POST   | `/qlisan/form` | The صرفي level alone, for a word typed with no verse position |
| POST   | `/tahlil/word` | The five-block integral analysis of one word |
| POST   | `/tahlil/review` | Mark one word's analysis reviewed by a named expert (durable; 503 with no store) |
| GET    | `/verse/{surah}/{ayah}` | One verse + neighbor context + adjacent ids (`?window=`) |
| GET    | `/surah/{number}` | Full surah: ordered verses + metadata + `basmala` |
| GET    | `/surahs`      | All 114 surahs (number, names, ayah count) for pickers |
| GET    | `/fassila/overview` | Fāṣila distribution across the whole corpus |
| GET    | `/fassila/{surah}` | Fāṣila derivation and run-structure for one surah |
| POST   | `/feedback`    | Record 👍/👎 on an answer |

**Removed — these now answer 404:** `POST /lexical`, `POST /lexical/stream`,
`POST /chat` (the non-streaming twin of `/chat/stream`), `POST /tahlil/verse`,
`GET /sessions/{id}` and `GET /feedback/stats`. None of them had a caller: chat
history is reassembled client-side, and a route no page calls is a route nobody
audits. `POST /madar/analyze` also 404s, but for a different reason — it is
quarantined rather than removed; see `linguistics/madar/__init__.py`.

```bash
curl "http://127.0.0.1:8000/search?q=%D8%A7%D9%84%D8%B5%D8%A8%D8%B1&surah=2&limit=3"

curl -N -X POST http://127.0.0.1:8000/chat/stream -H "Content-Type: application/json" \
  -d '{"messages":[{"role":"user","content":"Que dit le Coran sur la patience ?"}]}'

curl -X POST http://127.0.0.1:8000/lisan/analyze -H "Content-Type: application/json" \
  -d '{"word":"رحمة"}'
```

### Run the frontend (Next.js)

```bash
cd frontend
cp .env.local.example .env.local   # set NEXT_PUBLIC_API_URL to the backend
npm install
npm run dev                         # http://localhost:3000
```

Pages: `/` (project landing), `/chat` (streaming chat + sources + 👍/👎 feedback
+ health banner), `/verse-study` (Word in Verses + Similar Verses),
`/lexical` (Lisan: letter-level root reading), `/tahlil` (integral word
analysis), `/fassila` (fāṣila distribution), `/qlisan` (the per-word fiche,
reached from the other pages), and `/surah` + `/surah/[number]` +
`/verse/[surah]/[ayah]` (reading and deep-linking, Arabic-only). The API
base URL is read from `NEXT_PUBLIC_API_URL` — `npm run dev` picks up `.env.local`
automatically; for a production `npm run build`, set the variable before building
(it is inlined). The backend must allow the frontend origin via `CORS_ORIGINS`
(defaults to `http://localhost:3000`).

---

## Scripts reference

| Script | What it does |
|--------|--------------|
| `scripts/setup.sh` | Create `.venv`, install `requirements.txt`, copy `.env.example` → `.env` |
| `scripts/start_dev.sh` | `docker compose up -d ollama` — Qdrant is deliberately not started: with `QDRANT_PATH` set it runs embedded in the backend |
| `scripts/fetch_translations.py` | Download FR (Hamidullah) + EN (Sahih) translations → `data/derived/translations/` |
| `scripts/ingest.sh` | Run the ingestion pipeline (wrapper for `ingestion/run_pipeline.py`) |
| `scripts/build_maqayis_dataset.py` | Build the curated Maqāyīs aṣl reference `data/references/maqayis_asl.csv` from the OpenITI source |
| `scripts/build_root_cores_seed.py` | Seed `data/references/root_cores.json` from the Maqāyīs aṣl — the mechanical half of a root's semantic core. Dry run by default |
| `scripts/validate_lisan_datasets.py` | Validate the three curated Lisan datasets (axes, root cores, letter senses), enforce the letter-sheet freeze, and report coverage + the method indicator |
| `scripts/draw_islambouli_witness_set.py` | Draw the Islambouli measurement's 40-root holdout once (seed 20260928) through the shared harness; `--check` replays it |
| `scripts/record_islambouli_verdicts.py` | The Islambouli recording path: `bundle` (the blind uses-writers' input), `generate`, `worksheet`, `record`, `collisions` |
| `scripts/validate_islambouli_datasets.py` | Validate the Islambouli holdout, transcription, system-check grid, lock and record, and print `k / 40` beside the closed engine's with R1–R6 |
| `scripts/build_surah_similarity.py` | Build `data/derived/surah_similarity.json` (intra-surah close verses + groups). Backend stopped; `--dry-run` needs neither Qdrant nor a model |
| `scripts/eval_surah_similarity.py` | Report recall@10, per-stage losses and stored negatives of that build against the local gold set |
| `scripts/run.sh` | One-command launcher: Qdrant + Ollama + backend + frontend |

### Rebuilding the Maqāyīs reference

> The Maqāyīs CSV is **live**, not dormant. `POST /madar/analyze` is quarantined,
> but `linguistics/tahlil/evidence.py` reads Ibn Fāris' aṣl through the same
> `linguistics/madar/maqayis_store.py` rather than re-parsing it, so the Tahlīl
> page depends on this file.


`data/references/maqayis_asl.csv` (the curated Ibn Fāris *aṣl* per root) is
committed and is all the runtime needs. Its original — the ~3.8 MB OpenITI
text — is **git-ignored** (`data/source/maqayis/`) as a large, re-downloadable
file. To reconstitute it and rebuild the CSV from a fresh clone:

```bash
python scripts/build_maqayis_dataset.py --fetch   # downloads the OpenITI source, then parses → CSV
python scripts/build_maqayis_dataset.py           # re-parse a source already on disk
```

### Seeding and validating the Lisan datasets

Three committed files drive the constrained letter reading behind
`POST /lisan/analyze`: `data/references/semantic_axes.json` (the **closed** axis
vocabulary both other files tag against), `root_cores.json` (Ibn Fāris' attested
aṣl per root, keyed on the **canonical** QAC root spelling) and
`letter_senses.csv` (one row per letter + sense). None of them is regenerable —
their citation half comes from `maqayis_asl.csv`, everything else is human
judgement.

**Validate after every edit to any of the three**, before committing:

```bash
python scripts/validate_lisan_datasets.py   # exit 0 = clean, 1 = every finding listed
```

It checks that axis ids are unique and every `antonym` is declared from **both**
sides; that every core key is a real canonical QAC root key — never the
hamza-folded form `maqayis_asl.csv` is indexed on, which matches ~0 hamzated
roots and fails silently; that every `verbatim` is byte-identical to its Maqāyīs
segment, one core per aṣl and in the same order; that the citation names the
right work and the row's own `edition`; that `axes` is non-empty and `polarity`
set; that no core exists for a `no_asl` or `parse_uncertain` root; and that every
base letter carries at least one sense, with ids unique per letter and the enums
respected.

Two rules are worth knowing before curating:

- **A citation is checked against the authority it names, not merely filled in.**
  `page: "0"` and `source: "حدسي"` are both non-empty and both worthless, so a
  sense's `page` must equal the locus its letter is registered at in
  `data/references/arabic_letter_semantics_hasan_abbas.json`, and its `source`
  must be one of the letter-level authorities the validator allows (today, only
  Ḥasan ʿAbbās). Adding an authority — Ibn Jinnī, say — is a one-line, visible
  edit to `LETTER_SENSE_SOURCES`, not something a row can smuggle in. This is the
  gate `linguistics/tahlil/citations.py` applies to generated prose, applied to
  curated scholarship, and it is the only mechanical defence against curating a
  sense to fit the root in front of you.
- **An entry may not name both poles of an antonym pair.** A core tagged
  `["khubth", "tib"]` conflicts with every sense at once, so the root reads
  entirely unmatched and nothing in the response points at the dataset.

- **`position` is a gate, and it is `;`-separated.** A sense applies only where
  its authority scopes it; `any` — the value of most rows — means the authority
  states no position, so it applies everywhere. A sense may name two positions,
  because Ḥasan ʿAbbās does («في الآخر والوسط» is one predicate). The gate made
  `final` mean «only at the end» where it had meant «prefers the end», so every
  value was re-read under that stronger sense at lock v1.1.0; three rows whose
  authority is comparative are flagged in the lock's history, not changed.
  Never fill a position the author does not state: `any` is the honest default.

- **The letter sheet is FROZEN, and the validator enforces it.**
  `letter_senses.lock.json` pins a semantic `version` plus the sha256 of
  `letter_senses.csv`'s raw bytes. Roots are curated against a FIXED sheet,
  because the failure this guards looks like a success: a root matches nothing,
  a sense gets added to one of its letters, the root now "works" — and nothing
  records that the evidence was written to fit the conclusion. So a root that
  matches nothing is a RESULT (the report names it), and a letter changes only
  through a new version whose `history` entry cites the letter-level authority
  behind it — and that citation is CHECKED, not merely present: `source` is
  `{authority, pages}`, the authority must be one the validator knows, and every
  page range must be one `arabic_letter_semantics_hasan_abbas.json` actually
  declares. It used to be prose, and a draft of the 1.1.0 entry carried nine
  invented page ranges before a manual re-read caught them; a justification
  nobody can follow back makes the whole freeze decorative, because it looks
  like evidence and costs nothing to fabricate. The same authority index backs
  this and the per-row `page` check, so the two cannot drift. The failure message names
  the only two ways out — revert, or version it — and never "add the sense".
  `build_root_cores_seed.py` may never reach the sheet; two tests pin that, one
  reading its source and one checking the digest survives a `write()`.

It prints curated-core coverage and the Maqāyīs ceiling on every run, clean or
not, because that figure is where the next curation batch starts.
`tests/test_lisan_datasets.py` drives the same functions, so the rules exist once.

It also prints a **method indicator**, computed by running the real selection
step over the curated set (a metric computed by a second copy of the algorithm
measures the copy):

- **unmatched rate** — letter slots no sense was eligible for. High while
  coverage is thin, and that is healthy: it is the system declining to assert.
- **divergence rate** — readings whose aggregate pole contradicts their own
  core's polarity. This is the falsifiability probe, and the verdict line reads
  it: below 50 curated roots it says «not yet testable»; at or past 50 with the
  guard still never fired it says «**NOT FALSIFIABLE**», because a guard that
  detects and never corrects, staying silent over a large set, is the shape that
  curating letters to fit the cores would leave. The rates are only meaningful
  as a trend, which is why every run leaves its figures behind.

**Seed** the mechanical half of a batch of new roots — the canonical key,
`verbatim`, `source`, `edition`. `gloss`, `axes` and `polarity` are readings of
the citation and are left blank for a human:

```bash
python scripts/build_root_cores_seed.py           # DRY RUN — reports what it would add
python scripts/build_root_cores_seed.py --write   # apply: add the missing entries
```

Dry run is the default because the target is a hand-curated reference. The report
counts what it would add, what it preserves, what it skips and why, and names any
**orphan** key already on file that is not a canonical QAC root — a folded
spelling, typically, which the validator refuses downstream.

**Re-running never overwrites curated axes or polarity:** a root already on file
is preserved byte for byte and only absent roots are added — which is why
`quran_data/manifest.py` records `root_cores.json` as **not regenerable** even
though it names a producer. The script reproduces the seed, never the file. Note
that a freshly seeded entry has an empty `axes` and a null `polarity`, which the
validator refuses on purpose: `--write` output is a curation worklist, not a
shippable dataset. An existing `meta` block is carried forward untouched and the
script puts **no derivable count** in one — a stored count is a number that stops
being true on the first `--write`, and the validator recomputes every such figure
without ever reading that block.

## Gotchas

- **`.env` hostnames:** `.env.example` uses Docker-internal hostnames
  (`qdrant:6333`, `ollama:11434`). For host runs (uvicorn/scripts on your
  machine), switch them to `localhost` — this is the most common first error.
- **First run is heavy:** the embedding model (~1–2 GB) and `qwen2.5:7b`
  (~4.7 GB) download on first use; keep ≥ 8 GB RAM free.
- **Memory on a 16 GB Mac.** Models are loaded on demand — the embedder and the
  `/search` reranker are built by the first request that needs them, so a session
  spent on the Arabic study tools holds no model memory. Two settings matter more
  than anything else: set **`QDRANT_PATH=data/runtime/qdrant`** to run Qdrant
  in-process (no Docker VM at all — the corpus is 24 MB), and keep
  **`OLLAMA_KEEP_ALIVE`** short (`10m`). On Apple Silicon a loaded model is wired
  GPU memory that macOS cannot swap, so a long keep_alive starves everything else
  for that whole window. Embedded Qdrant takes an exclusive lock: stop the backend
  before running `build_index.py`.
- **A full disk turns memory pressure into a freeze.** macOS grows its swapfile on
  demand; with a nearly full SSD it cannot, and the machine hard-locks instead of
  killing a process. Keep some tens of GB free.
- **Two backend ports:** examples here use `:8000`; `run.sh` defaults to `:8000`
  too but is overridable. Keep `NEXT_PUBLIC_API_URL` in sync with whichever you use.
