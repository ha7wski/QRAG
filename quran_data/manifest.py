"""
manifest.py — what each dataset is, where it came from, who reads it.

One entry per dataset. This is the single home for provenance: it used to be
spread across `CLAUDE.md`, `scripts/README.md` and a dozen module docstrings
that agreed only partially, plus a local-only audit under `eval/` that was
deleted with the workbench it belonged to.

The entries answer the questions a reader actually has:

  * **Can I delete this?** `regenerable` says so, and `rebuild` gives the exact
    command. Nothing under `source/` or `references/` is regenerable — those are
    third-party originals and curated human decisions, and no script in this repo
    can reproduce either.
  * **Where did it come from?** `origin` names the upstream project, its URL, or
    the script that fetches it.
  * **Who breaks if it goes missing?** `consumers` lists the modules that read it.

`tests/test_quran_data.py` asserts this file and `paths.py` cannot drift apart:
every path constant has an entry, every entry names a real constant, and every
consumer it lists is a module that exists.
"""
from __future__ import annotations

from typing import NamedTuple

# Constants in `paths.py` that name a bucket directory rather than a dataset.
# The coverage test skips these; everything else must be described below.
BUCKET_CONSTANTS = frozenset(
    {"ROOT", "DATA", "SOURCE", "REFERENCES", "DERIVED", "RUNTIME", "TRANSLATIONS"}
)

PIPELINE = "python ingestion/run_pipeline.py"


class Entry(NamedTuple):
    """One dataset's identity card."""

    bucket: str                    # source | references | derived | runtime
    what: str                      # one line: shape and size
    origin: str                    # upstream project, URL, or fetching script
    producer: str | None           # the step that writes it; None = third-party
    consumers: tuple[str, ...]     # modules that read it
    regenerable: bool
    rebuild: str | None = None     # exact command, when regenerable


MANIFEST: dict[str, Entry] = {
    # ── source ────────────────────────────────────────────────────────────
    "QURAN_CSV": Entry(
        bucket="source",
        what="6236 verses, undiacritized Arabic plus the surah name (846 KB).",
        origin="Third-party Quran text corpus, committed to this repo.",
        producer=None,
        consumers=("ingestion/parser.py",),
        regenerable=False,
    ),
    "QURAN_CHAKL_CSV": Entry(
        bucket="source",
        what="6236 verses, fully vocalized Arabic in imlāʾī orthography (1.4 MB). "
             "Prepends the Basmala to ayah 1 of 113 surahs — see "
             "`strip_leading_basmala`.",
        origin="Third-party vocalized Quran corpus, committed to this repo.",
        producer=None,
        consumers=(
            "quran_data/corpus.py",
            "ingestion/qac_treebank.py",
            "retrieval/verse_lookup.py",
        ),
        regenerable=False,
    ),
    "QAC_MORPHOLOGY_TXT": Entry(
        bucket="source",
        what="130 030 morphological segments, TAB-separated, four columns "
             "(s:a:w:seg, form, tag, features) (6.0 MB). Chain A of root "
             "resolution, and the only artefact that preserves the hamza seat "
             "of a root (`أ` vs `ء`).",
        origin="Quranic Arabic Corpus (Leeds, Dukes) via the mustafa0x/"
               "quran-morphology fork, whose roots are manually verified. "
               "https://github.com/mustafa0x/quran-morphology",
        producer=None,
        consumers=("quran_data/qac.py",),
        regenerable=False,
    ),
    "TREEBANK_CSV": Entry(
        bucket="source",
        what="139 376 rows, 45 columns: per-segment morphology AND dependency "
             "syntax (31 MB). Chain B of root resolution, and the repo's only "
             "naḥwī foundation.",
        origin="The NoorBayan «Quranic» dependency treebank, shipped as the "
               "archive `Quranic.rar` (containing a single `Quranic.csv`) "
               "alongside `Quran.csv`, `RelLabels.csv` and `pos.csv`. Its "
               "`features` column carries QAC 0.4 in raw Buckwalter and is "
               "99.25 % identical to it. Those four companion files were "
               "untracked in this change: nothing read them (the treebank "
               "already inlines `pos_ar` and `rel_label_ar`), and this entry "
               "is what keeps their provenance on record.",
        producer=None,
        consumers=("ingestion/qac_treebank.py", "ingestion/root_resolver.py"),
        regenerable=False,
    ),
    "MAQAYIS_SOURCE_TXT": Entry(
        bucket="source",
        what="44 783 lines of Ibn Fāris's *Muʿjam Maqāyīs al-Luġa* (3.8 MB). "
             "Git-ignored: large, re-downloadable, and only its curated "
             "derivative ships.",
        origin="OpenITI 0400AH corpus. "
               "https://raw.githubusercontent.com/OpenITI/0400AH/master/data/ "
               "— fetch with `python scripts/build_maqayis_dataset.py --fetch`.",
        producer=None,
        consumers=("scripts/build_maqayis_dataset.py",),
        regenerable=False,
    ),

    # ── references: curated scholarship, each carrying a human decision ───
    "ROOT_ARBITRATION_JSON": Entry(
        bucket="references",
        what="30 hand-decided root families, each with its deciding rule and a "
             "cited authority (a Maqāyīs entry, or corpus evidence).",
        origin="Hand-written. The only channel through which a stored root may "
               "deviate from the reference source. Regenerating it would "
               "discard the arbitration itself.",
        producer=None,
        consumers=("ingestion/root_resolver.py",),
        regenerable=False,
    ),
    "MAQAYIS_ASL_CSV": Entry(
        bucket="references",
        what="4662 roots → Ibn Fāris's aṣl (765 KB); has_asl 3326, "
             "parse_uncertain 1322, no_asl 14.",
        origin="Built once from MAQAYIS_SOURCE_TXT by "
               "`scripts/build_maqayis_dataset.py`. Curated scholarship, kept "
               "in the reference bucket rather than treated as a build "
               "artefact — Madār is quarantined but this file is not its "
               "by-product.",
        producer="scripts/build_maqayis_dataset.py",
        consumers=("linguistics/madar/maqayis_store.py",),
        regenerable=False,
    ),
    "ARABIC_LETTERS_CSV": Entry(
        bucket="references",
        what="28 base letters: identity and phonetics only — makhraj and ṣifāt "
             "(ar+en), an Ibn Jinnī sound-imitation note. The `abbas_meaning*` "
             "and `abbas_keywords*` columns were DROPPED: one frozen gloss per "
             "letter is what made خ-ي-ر read «القذارة والخشونة والخواء». Sense "
             "data now lives in LETTER_SENSES_CSV, joined on `letter`.",
        origin="Curated from Ḥasan ʿAbbās, *Khaṣāʾiṣ al-ḥurūf al-ʿarabiyya wa-"
               "maʿānīhā*, at `confidence='summary'` granularity.",
        producer=None,
        consumers=("linguistics/lisan/letter_lexicon.py",),
        regenerable=False,
    ),
    "LETTER_SENSES_CSV": Entry(
        bucket="references",
        what="One row per (letter, sense): gloss_ar, pole, axes, position, "
             "gesture_ar, source, page, confidence. 59 senses over the 28 base "
             "letters — a letter holds a BUNDLE, and which member applies "
             "depends on the root's attested core, so nothing here is ranked.",
        origin="Transcribed from Ḥasan ʿAbbās, *Khaṣāʾiṣ al-ḥurūf al-ʿarabiyya "
               "wa-maʿānīhā* (1998), page-cited per sense. Senses taken from a "
               "letter's headline value are `verified`; those transcribed from "
               "his position-dependent remarks are `high`. A sense with no "
               "`source` AND `page` is refused by the validator.",
        producer=None,
        consumers=("linguistics/lisan/letter_lexicon.py",
                   "scripts/validate_lisan_datasets.py"),
        regenerable=False,
    ),
    "LETTER_SENSES_LOCK_JSON": Entry(
        bucket="references",
        what="The freeze on LETTER_SENSES_CSV: a semantic `version`, the sha256 "
             "of that file's raw bytes, its row/letter counts, and a `history` "
             "entry per version carrying the reason AND the letter-level "
             "authority that justifies it (2 KB).",
        origin="Written by hand at the end of the constrain-lisan-by-root-core "
               "change. Root curation runs against a FIXED letter sheet: a root "
               "that matches no sense is a result to record, never a reason to "
               "retouch a letter. The digest is what enforces that — editing the "
               "CSV without bumping the version here fails the validator.",
        producer=None,
        consumers=("scripts/validate_lisan_datasets.py",),
        regenerable=False,
    ),
    "ROOT_CORES_JSON": Entry(
        bucket="references",
        what="Attested semantic core(s) per root, keyed on the CANONICAL QAC "
             "root key (never the folded Maqāyīs key). Value is an ordered LIST "
             "— Ibn Fāris states two aṣl for ظلم — each with gloss / verbatim / "
             "axes / polarity / source. Cores are never merged and their axes "
             "are never pooled.",
        origin="Curated from MAQAYIS_ASL_CSV. `verbatim` is byte-identical to "
               "its segment there; only `gloss`, `axes` and `polarity` are the "
               "curator's. `polarity` describes the aṣl AS CITED — `neutral` "
               "when it is descriptive — never the root's Quranic connotation.",
        # Seeded by script, completed by a human: re-running the seed adds
        # missing entries and never overwrites curated axes or polarity, so the
        # file as a whole is NOT reproducible from the script.
        producer="scripts/build_root_cores_seed.py",
        consumers=("linguistics/lisan/root_core_store.py",
                   "scripts/validate_lisan_datasets.py"),
        regenerable=False,
    ),
    "SEMANTIC_AXES_JSON": Entry(
        bucket="references",
        what="The CLOSED axis vocabulary: 47 axes, each with an id, an Arabic "
             "label and an optional symmetric `antonym` link.",
        origin="Curated alongside the regression roots and the letters they "
               "use. Closed on purpose: selection is a set intersection between "
               "a core's axes and a sense's, so free-text axes would make "
               "agreement an accident of wording. The `antonym` link is what "
               "separates «no shared axis» from «an opposed axis».",
        producer=None,
        consumers=("linguistics/lisan/root_core_store.py",
                   "scripts/validate_lisan_datasets.py"),
        regenerable=False,
    ),
    "LETTER_SEMANTICS_JSON": Entry(
        bucket="references",
        what="29 letters: phonetic ṣifāt plus Ḥasan ʿAbbās's dalāla WITH page "
             "numbers, v0.2.0 (27 KB). Holds ء and ا as two distinct entries "
             "with distinct pages — which is why a hamza seat must survive.",
        origin="Curated from Ḥasan ʿAbbās, *Khaṣāʾiṣ al-ḥurūf al-ʿarabiyya wa-"
               "maʿānīhā*, cited per letter.",
        producer=None,
        consumers=("linguistics/tahlil/huruf.py",),
        regenerable=False,
    ),
    "BAB_CONTRAST_JSON": Entry(
        bucket="references",
        what="11 bāb contrasts, verbs only, v0.1.0 (12 KB).",
        origin="Hand-written from classical ṣarf.",
        producer=None,
        consumers=("linguistics/tahlil/form_kb.py",),
        regenerable=False,
    ),
    "SIGHA_DALALA_JSON": Entry(
        bucket="references",
        what="27 ṣīgha → possible-sense rules (24 KB); keys aligned with "
             "`linguistics/analysis/mizan.py`.",
        origin="Hand-written from classical ṣarf.",
        producer=None,
        consumers=("linguistics/tahlil/form_kb.py",),
        regenerable=False,
    ),
    "MIZAN_PATTERNS_JSON": Entry(
        bucket="references",
        what="2 curated awzān plus 4 special cases for broken plurals (6 KB). "
             "Corrects the mīzān where letter-by-letter projection fails.",
        origin="Hand-written. Lived outside `data/` entirely until this change.",
        producer=None,
        consumers=("linguistics/analysis/mizan.py",),
        regenerable=False,
    ),

    # ── derived: chain A, from QAC_MORPHOLOGY_TXT ─────────────────────────
    "MORPHOLOGY_JSON": Entry(
        bucket="derived",
        what="1651 roots → {forms, verses, count}, 44 718 occurrences at VERSE "
             "granularity (1.1 MB).",
        origin="Chain A.",
        producer="ingestion/qac_morphology.py",
        consumers=("retrieval/lexical_retriever.py", "scripts/build_maqayis_dataset.py"),
        regenerable=True,
        rebuild=PIPELINE,
    ),
    "QAC_RESOLUTION_JSON": Entry(
        bucket="derived",
        what="`form_to_roots` + `lem_to_roots` (452 KB) — resolves a typed word "
             "to its root(s).",
        origin="Chain A.",
        producer="ingestion/qac_morphology.py",
        consumers=("retrieval/lexical_retriever.py",),
        regenerable=True,
        rebuild=PIPELINE,
    ),
    "LEMMA_INDEX_JSON": Entry(
        bucket="derived",
        what="root → lemmas, dominant sense first (2.9 MB). Splits a root into "
             "its senses for «الكلمة في الآيات». Each lemma carries `word_refs` "
             "(`s:a:w`) beside `verses`: verse granularity alone cannot separate "
             "two lemmas of one root inside one verse (40:81 = آيَاتِهِ + فَأَيَّ, both "
             "أيي), which is what the highlighting needs.",
        origin="Chain A.",
        producer="ingestion/qac_morphology.py",
        consumers=("retrieval/verse_lookup.py",),
        regenerable=True,
        rebuild=PIPELINE,
    ),
    "PROPER_NOUNS_JSON": Entry(
        bucket="derived",
        what="62 rootless proper nouns (39 KB) — makes `إبراهيم` findable even "
             "though QAC gives it no root. Carries `word_refs` like the lemma "
             "index, so a name highlights by position, not by substring.",
        origin="Chain A.",
        producer="ingestion/qac_morphology.py",
        consumers=("retrieval/verse_lookup.py",),
        regenerable=True,
        rebuild=PIPELINE,
    ),
    "ROOTS_RESOLVED_JSON": Entry(
        bucket="derived",
        what="`s:a:w` → {primary, alternates, rule} — the arbitrated root of "
             "every word, decided once ahead of both chains.",
        origin="Arbitration between QAC_MORPHOLOGY_TXT (chain A) and "
               "TREEBANK_CSV (chain B), with ROOT_ARBITRATION_JSON as the "
               "recorded-verdict channel. The resolver RAISES rather than "
               "writing when a disagreement is unarbitrated.",
        producer="ingestion/root_resolver.py",
        consumers=("ingestion/qac_morphology.py", "ingestion/qac_treebank.py"),
        regenerable=True,
        rebuild=PIPELINE,
    ),

    # ── derived: chain B, from TREEBANK_CSV ───────────────────────────────
    "QAC_WORDS_JSON": Entry(
        bucket="derived",
        what="77 429 words → full morphology: root, lemma, POS, features, "
             "segments, is_proper_noun (29 MB). The ṣarfī foundation.",
        origin="Chain B.",
        producer="ingestion/qac_treebank.py",
        consumers=("linguistics/analysis/qlisan_data.py",),
        regenerable=True,
        rebuild=PIPELINE,
    ),
    "QAC_SYNTAX_JSON": Entry(
        bucket="derived",
        what="76 639 words → dependency role (relation, head_ref) (7.6 MB). The "
             "repo's only naḥwī foundation; words with no usable relation are "
             "omitted, which is what makes `nahwi.available` false.",
        origin="Chain B.",
        producer="ingestion/qac_treebank.py",
        consumers=("linguistics/analysis/qlisan_data.py",),
        regenerable=True,
        rebuild=PIPELINE,
    ),
    "WORD_FUNCTION_JSON": Entry(
        bucket="derived",
        what="The 297 words that serve as a grammatical TOOL rather than carry "
             "their own meaning: `s:a:w` → أداة نداء | أداة استفهام | أداة شرط "
             "(10 KB). «الكلمة في الآيات» FILTERS them out — «أيها» is a calling "
             "formula and is not an occurrence of آية «sign». The cost is real and "
             "accepted: كيف keeps 3 of its 83 occurrences. No root is emptied.",
        origin="Chains A and B together: the morphology's VOC+ATT / INTG / COND "
               "markers, unioned with the treebank's `role_ar` (حرف استفهام, حرف "
               "شرط). Neither layer sees every case on its own.",
        producer="ingestion/qac_treebank.py",
        consumers=("retrieval/verse_lookup.py",),
        regenerable=True,
        rebuild=PIPELINE,
    ),
    "WORD_PREFIXES_JSON": Entry(
        bucket="derived",
        what="`s:a:w` → the joined PREFIX segments of the 26 001 of 77 429 words "
             "that open with one, 108 distinct strings (0.5 MB). What makes a "
             "لفظ in «الكلمة في الآيات» the written word MINUS its proclitics "
             "(`بِـَٔايَٰتِنَا` and `ءَايَٰتِنَا` are both آياتنا) without inferring them "
             "from the leading letters — a rule that would turn `وَلَد` into `لد`.",
        origin="Chain B: an EXTRACT of QAC_WORDS_JSON's `segments_detail`, "
               "written by the same run so the two cannot drift. Extracted "
               "rather than read in place because `qac_words.json` costs 248 MB "
               "resident against `word_index.json`'s 64 MB, and the lookup path "
               "holds neither today.",
        producer="ingestion/qac_treebank.py",
        consumers=("retrieval/verse_lookup.py",),
        regenerable=True,
        rebuild=PIPELINE,
    ),
    "ROOT_GRAPH_JSON": Entry(
        bucket="derived",
        what="1642 roots → 49 967 `s:a:w` refs at WORD granularity (565 KB). "
             "Powers naẓāʾir and usage attestation.",
        origin="Chain B.",
        producer="ingestion/qac_treebank.py",
        consumers=("linguistics/analysis/qlisan_data.py", "linguistics/tahlil/huruf.py",
                   "retrieval/verse_lookup.py"),
        regenerable=True,
        rebuild=PIPELINE,
    ),
    "WORD_INDEX_JSON": Entry(
        bucket="derived",
        what="77 429 words → {uthmani, imlaai, chakl_char_start, chakl_char_end, "
             "aligned} (9.2 MB). THE ALIGNMENT SPINE: a UI token index equals a "
             "QAC word index. Its char offsets are computed against the "
             "Basmala-INCLUSIVE chakl rows.",
        origin="Chain B, aligned onto QURAN_CHAKL_CSV.",
        producer="ingestion/qac_treebank.py",
        consumers=("linguistics/analysis/qlisan_data.py", "linguistics/tahlil/evidence.py",
                   "retrieval/verse_lookup.py"),
        regenerable=True,
        rebuild=PIPELINE,
    ),
    "OVERRIDES_JSON": Entry(
        bucket="derived",
        what="6 hand-resolved alignment cases (1 KB) — a build escape hatch that "
             "is consumed as data rather than hard-coded.",
        origin="Hand-written, but read back by the build it corrects.",
        producer="ingestion/qac_treebank.py",
        consumers=("ingestion/qac_treebank.py",),
        regenerable=True,
        rebuild=PIPELINE,
    ),
    "QLISAN_ALIGNMENT_AUDIT_JSON": Entry(
        bucket="derived",
        what="Build coverage report (179 B). Written, never read back.",
        origin="Chain B build trace.",
        producer="ingestion/qac_treebank.py",
        consumers=(),
        regenerable=True,
        rebuild=PIPELINE,
    ),

    # ── derived: pipeline stage snapshots and the serving corpus ──────────
    "VERSES_RAW_JSON": Entry(
        bucket="derived",
        what="6236 verses, stage-1 snapshot (2.8 MB). Same schema as "
             "`verses_final`; nothing reads it.",
        origin="Stage 1 of the ingestion pipeline.",
        producer="ingestion/parser.py",
        consumers=(),
        regenerable=True,
        rebuild=PIPELINE,
    ),
    "VERSES_ENRICHED_JSON": Entry(
        bucket="derived",
        what="6236 verses, stage-3 snapshot (3.7 MB). Same schema as "
             "`verses_final`; nothing reads it.",
        origin="Stage 3 of the ingestion pipeline.",
        producer="ingestion/enricher.py",
        consumers=(),
        regenerable=True,
        rebuild=PIPELINE,
    ),
    "VERSES_FINAL_JSON": Entry(
        bucket="derived",
        what="6236 verses, full schema including the `roots` field (6.0 MB). "
             "THE SERVING CORPUS — the backend and the indexer both load it.",
        origin="End of the ingestion pipeline.",
        producer="ingestion/qac_morphology.py",
        consumers=(
            "quran_data/corpus.py",
            "indexing/build_index.py",
            "indexing/bm25_index.py",
        ),
        regenerable=True,
        rebuild=PIPELINE,
    ),
    "BM25_INDEX_PKL": Entry(
        bucket="derived",
        what="{bm25, verse_ids} — the sparse index over ar+fr+en (4.1 MB). The "
             "lexical branch of the RRF fusion.",
        origin="Built from VERSES_FINAL_JSON plus the translations.",
        producer="indexing/build_index.py",
        consumers=("indexing/bm25_index.py",),
        regenerable=True,
        rebuild="python indexing/build_index.py",
    ),
    "BUILD_INDEX_CHECKPOINT": Entry(
        bucket="derived",
        what="Resume marker for the embedding run — not a dataset. Deleting it "
             "costs a full re-embed of 6236 verses, nothing else.",
        origin="Written by the indexer as it progresses.",
        producer="indexing/build_index.py",
        consumers=("indexing/build_index.py",),
        regenerable=True,
        rebuild="python indexing/build_index.py",
    ),
    "TRANSLATION_FR_JSON": Entry(
        bucket="derived",
        what="6236 French translations, Hamidullah (974 KB). Indexed by BM25 "
             "AND embedded by E5 — indexing translations raised hit-rate@10 "
             "from ~0.70 to ~0.90.",
        origin="alquran.cloud open API, https://api.alquran.cloud/v1/quran/",
        producer="scripts/fetch_translations.py",
        consumers=("ingestion/translator.py",),
        regenerable=True,
        rebuild="python scripts/fetch_translations.py",
    ),
    "TRANSLATION_EN_JSON": Entry(
        bucket="derived",
        what="6236 English translations, Sahih International (929 KB).",
        origin="alquran.cloud open API, https://api.alquran.cloud/v1/quran/",
        producer="scripts/fetch_translations.py",
        consumers=("ingestion/translator.py",),
        regenerable=True,
        rebuild="python scripts/fetch_translations.py",
    ),

    # ── runtime: mutable state the running app owns ───────────────────────
    "DEFAULT_APP_DB": Entry(
        bucket="runtime",
        what="SQLite: chat sessions and 👍/👎 feedback. Override with "
             "`APP_DB_PATH`.",
        origin="Written by the app as it serves.",
        producer="api/store.py",
        consumers=("api/store.py",),
        regenerable=True,
        rebuild="Deleting it loses the history; the app recreates an empty one.",
    ),
    "DEFAULT_QDRANT_DIR": Entry(
        bucket="runtime",
        what="Embedded Qdrant collection, 6236 vectors (~24 MB). Override with "
             "`QDRANT_PATH`; an EMPTY value means server mode at `QDRANT_URL`. "
             "Takes an exclusive file lock, so the backend and the indexer "
             "cannot both hold it.",
        origin="Written by the indexer.",
        producer="indexing/build_index.py",
        consumers=("indexing/qdrant_store.py",),
        regenerable=True,
        rebuild="python indexing/build_index.py --rebuild  (backend stopped)",
    ),
    "DEFAULT_TAHLIL_COVERAGE_TSV": Entry(
        bucket="runtime",
        what="Append-only log of rejected Tahlīl claims. Override with "
             "`TAHLIL_COVERAGE_LOG`, which is what keeps a test run off the "
             "real file.",
        origin="Written by the app as it serves.",
        producer="linguistics/tahlil/coverage.py",
        consumers=("linguistics/tahlil/coverage.py",),
        regenerable=True,
        rebuild="Deleting it loses the measurement; the app recreates it.",
    ),
}
