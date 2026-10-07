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
    "ISLAMBOULI_POSTER_PNG": Entry(
        bucket="source",
        what="The poster reproducing Samer Islambouli's letter table, 1132×1646 "
             "PNG, sha256 e64906b3b351539cc600f1bff88c9156b703142f740df5a691fac56feabcac0c. "
             "Its title band, banner and footer print the table's title, the book "
             "(«علمية اللسان العربي وعالميته») and the author.",
        origin="Supplied by the user; origin unrecorded. The original replaced a "
               "truncated first deposit before any transcription.",
        producer=None,
        consumers=("scripts/validate_islambouli_datasets.py",),
        regenerable=False,
    ),
    "ISLAMBOULI_MAFAHIM_DRB_PNG": Entry(
        bucket="source",
        what="Video screenshot, 1888×1004 PNG: Islambouli's ضرب, under «الحالة "
             "الفيزيائية» and «الحالة الثقافية», programme «مفاهيم».",
        origin="Supplied by the user; origin unrecorded (no episode reference).",
        producer=None,
        consumers=("linguistics/lisan/islambouli_citations.py",),
        regenerable=False,
    ),
    "ISLAMBOULI_MAFAHIM_KTB_PNG": Entry(
        bucket="source",
        what="Video screenshot, 1936×998 PNG: Islambouli's كتب, labelled «( مفهوم )», "
             "programme «مفاهيم».",
        origin="Supplied by the user; origin unrecorded (no episode reference).",
        producer=None,
        consumers=("linguistics/lisan/islambouli_citations.py",),
        regenerable=False,
    ),
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
             "position_kind, gesture_ar, source, page, confidence. 58 senses "
             "over the 28 base "
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
    "PHYSICAL_PRIMITIVES_CSV": Entry(
        bucket="references",
        what="16 rows, one per (ṣifa feature, primitive), over a CLOSED "
             "vocabulary of 15 primitives — the whole input of the "
             "physics-first concept engine (2 KB). Keyed on the feature "
             "vocabulary alone: it holds no root, no root key and no per-root "
             "exception. Every row carries a `status` (`attested` | "
             "`hypothesis`), a `physical_basis` and the lemma set a phrasing "
             "pass may realise it with.",
        origin="Written by hand against the ṣifāt vocabulary — before the first "
               "root was composed and before the collision probe ran. Every row "
               "ships as `hypothesis`: no known source tabulates the ṣifāt into "
               "a general quality-to-notion mapping, so the table is this "
               "project's own construction and says so. That is the condition "
               "under which k/40 can falsify it.",
        producer=None,
        consumers=(
            "linguistics/lisan/concept/primitives.py",
            "scripts/validate_concept_datasets.py",
        ),
        regenerable=False,
    ),
    "PHYSICAL_PRIMITIVES_LOCK_JSON": Entry(
        bucket="references",
        what="The freeze on PHYSICAL_PRIMITIVES_CSV: `version`, `frozen_on`, "
             "the sha256 of that file's raw bytes, its row/feature/primitive "
             "counts, and a `history` entry per version carrying its reason and "
             "a machine-checkable `source` (2 KB).",
        origin="Written by hand at the moment the table was frozen. The table "
               "changes only through a new version here justified by a "
               "FEATURE-level authority — never by a root that read badly, "
               "which is back-fitting. history[0] records that the table is the "
               "project's construction and borrows no authority.",
        producer=None,
        consumers=(
            "linguistics/lisan/concept/primitives.py",
            "scripts/validate_concept_datasets.py",
        ),
        regenerable=False,
    ),
    "CONCEPT_COLLISION_PROBE_JSON": Entry(
        bucket="references",
        what="The §D13 collision-probe record: the fixed comparison criterion, "
             "the probe's size in ROOTS (7 over 3 classes), the qualification "
             "table with every probe root's whole aṣl set read from "
             "MAQAYIS_ASL_CSV and a qualifying/non-qualifying verdict per "
             "comparison, and — appended later — the probe's realised "
             "primitives, per-pair outcome and verdict (14 KB).",
        origin="The qualification half was written by hand and committed BEFORE "
               "any concept was composed, so the test's denominator is fixed "
               "before its result is known. The probe half is appended by "
               "`scripts/run_collision_probe.py`, which refuses to run without "
               "the qualification and records its digest.",
        producer=None,
        consumers=("scripts/run_collision_probe.py",),
        regenerable=False,
    ),
    "CONCEPT_WITNESS_SET_JSON": Entry(
        bucket="references",
        what="The 40-root frozen holdout for k/40, with the frame (280 roots), "
             "the two strata (205 / 75), the seed (20260925), the draw date, "
             "the exclusions and the replayable procedure (6 KB).",
        origin="Drawn once with `random.Random(20260925)` before the primitive "
               "table was written, from triliteral QAC roots that carry a "
               "Maqāyīs `has_asl` row and ≥20 occurrences, minus the 5 roots "
               "already curated in root_cores.json and the development case "
               "ضرب. Committed to data/references/ rather than tests/ — which "
               "is git-ignored — because a metric nobody cloning the repo can "
               "re-derive is not a published metric.",
        producer=None,
        consumers=("scripts/validate_concept_datasets.py",),
        regenerable=False,
    ),
    "ISLAMBOULI_LETTERS_CSV": Entry(
        bucket="references",
        what="Samer Islambouli's letter table, 29 rows (poster rows 0–28): "
             "`row`, `label_as_printed`, `text_as_printed`, `text` (identical "
             "up to whitespace), `status` = transcribed_from_poster, "
             "`reading_note` (4 KB).",
        origin="Transcribed by hand from data/source/islambouli_letters_poster.png, "
               "every row read at 3× on the original image. Nothing is curated: a "
               "row changes only to correct a transcription error proved against "
               "the image, through a new lock version.",
        producer=None,
        consumers=("scripts/validate_islambouli_datasets.py",
                   "linguistics/lisan/islambouli/table.py",
                   "api/routers/lisan.py"),
        regenerable=False,
    ),
    "ISLAMBOULI_LETTERS_LOCK_JSON": Entry(
        bucket="references",
        what="The freeze on islambouli_letters.csv: version, date, sha256 of the "
             "CSV bytes, and a history whose source names the authority, the "
             "witness image and its digest, the poster's transcribed imprint "
             "(title band, banner, footer, top edge), an empty `pages` and the "
             "attribution basis.",
        origin="Written once when the transcription was frozen, before any uses "
               "of the second holdout existed. Changes only through a new "
               "version correcting a transcription error proved on the image.",
        producer=None,
        consumers=("scripts/validate_islambouli_datasets.py",
                   "linguistics/lisan/islambouli/table.py"),
        regenerable=False,
    ),
    "ISLAMBOULI_WASF_CSV": Entry(
        bucket="references",
        what="The closed مصدر → وصف table of the physical-stage assembly: `masdar`, "
             "`wasf`, `form`, `justification`; 4 entries, ceiling 20.",
        origin="Enumerated from the first words of the Islambouli rows' "
               "alternatives and admitted by one morphological criterion (both "
               "participles share one unvocalized spelling), never by a root.",
        producer=None,
        consumers=("linguistics/lisan/islambouli/wasf.py",),
        regenerable=False,
    ),
    "ISLAMBOULI_WASF_LOCK_JSON": Entry(
        bucket="references",
        what="The freeze on islambouli_wasf.csv: version, sha256, criterion, "
             "rejected candidates, and the assembly's segment notes (rows ء ع ض).",
        origin="Written when the table was frozen, before any root other than the "
               "two development cases was assembled.",
        producer=None,
        consumers=("linguistics/lisan/islambouli/wasf.py",),
        regenerable=False,
    ),
    "ISLAMBOULI_CITATIONS_JSON": Entry(
        bucket="references",
        what="Islambouli's published root statements: per entry `root`, `stage` "
             "(physical | cultural), label and text as printed, `text`, source "
             "with witness digest; plus the declared development cases.",
        origin="Transcribed by hand at 2× from the «مفاهيم» screenshots under "
               "data/source/.",
        producer=None,
        consumers=("linguistics/lisan/islambouli_citations.py",),
        regenerable=False,
    ),
    "ISLAMBOULI_CITATIONS_LOCK_JSON": Entry(
        bucket="references",
        what="The freeze on islambouli_citations.json: version, sha256, history.",
        origin="Written when the citations were frozen.",
        producer=None,
        consumers=("linguistics/lisan/islambouli_citations.py",),
        regenerable=False,
    ),
    "ISLAMBOULI_LETTERS_GRID_JSON": Entry(
        bucket="references",
        what="The system check of the Islambouli table: per row, alternatives "
             "and action / intensity / ending slots in the poster's own words, "
             "the one rule ambiguity (row 14) and the criteria, hypotheses and "
             "verdict under both of its readings.",
        origin="Decomposed by hand under design.md §D11's rules, fixed before "
               "the grid existed. The `result` block is written by the validator's "
               "evaluate_grid(), never typed, and is recomputed on every run.",
        producer=None,
        consumers=("scripts/validate_islambouli_datasets.py",),
        regenerable=False,
    ),
    "ISLAMBOULI_ATTESTATION_JSON": Entry(
        bucket="references",
        what="The Islambouli confrontation record k/40 is computed from: per "
             "witness root, uses (gloss + one own verse) frozen before its "
             "reading existed, then per-use verdicts with a classed reason on "
             "every miss; `ضرب` with its closed-run uses and a blind calibration "
             "copy.",
        origin="Uses written by blind sub-agents from a reproducible bundle "
               "(scripts/record_islambouli_verdicts.py bundle); prompts, raw "
               "outputs' digests and the bundle digests are in the meta. "
               "Verdicts by the curator under the inherited criterion.",
        producer="scripts/record_islambouli_verdicts.py",
        consumers=("scripts/validate_islambouli_datasets.py",),
        regenerable=False,
    ),
    "ISLAMBOULI_WITNESS_SET_JSON": Entry(
        bucket="references",
        what="The second 40-root holdout, for the Islambouli letter table: seed "
             "20260928, the frame it was drawn from (280 minus the first "
             "holdout's 40 = 176 + 64), the preconditions it asserted, the "
             "replayable procedure, and the draw's recorded structure.",
        origin="Drawn once by scripts/draw_islambouli_witness_set.py through "
               "linguistics/lisan/harness/draw.py — the code that also replays "
               "the first draw — and committed before any row of the table was "
               "transcribed. Never re-drawn: a draw repeated until it looks "
               "convenient is not a holdout.",
        producer="scripts/draw_islambouli_witness_set.py",
        consumers=("scripts/validate_islambouli_datasets.py",
                   "linguistics/lisan/islambouli/witness_guard.py"),
        regenerable=False,
    ),
    "CONCEPT_ATTESTATION_JSON": Entry(
        bucket="references",
        what="The confrontation record k/40 is computed from: per witness root, "
             "the Quranic uses frozen before its concept existed (`uses[]`, each "
             "a gloss, a verse and a `covered`/`not_covered` verdict carrying "
             "its one-line reason on a miss), plus `uses_frozen_at` and "
             "`concept_recorded_at`. Ships as a SKELETON — `roots` empty — "
             "because a record written ahead of its curation would be the one "
             "thing the file exists to prevent.",
        origin="Curated by hand, one root at a time, and the ORDER is the "
               "dataset: each root's `uses[]` is committed BEFORE that root's "
               "concept is generated. Written afterwards, the list shapes itself "
               "around the sentence — silently and in good faith — and coverage "
               "stops measuring anything. `scripts/validate_concept_datasets.py` "
               "refuses to print the metric for any root whose stamps are the "
               "wrong way round, and a root whose concept misses a use stays "
               "recorded as a miss: never a reason to edit the primitive table.",
        producer=None,
        consumers=(
            "linguistics/lisan/concept/confront.py",
            "scripts/validate_concept_datasets.py",
        ),
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
        consumers=("retrieval/lexical_retriever.py", "scripts/build_maqayis_dataset.py",
                   "scripts/build_quran_passages.py"),
        regenerable=True,
        rebuild=PIPELINE,
    ),
    "QAC_RESOLUTION_JSON": Entry(
        bucket="derived",
        what="`form_to_roots` + `lem_to_roots` + `word_to_roots` — resolves a "
             "typed word to its root(s). `word_to_roots` is keyed on the whole "
             "words the Quran writes (يؤمنون, قالوا), each paired with its QAC word.",
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
        consumers=("ingestion/qac_morphology.py", "ingestion/qac_treebank.py",
                   "scripts/build_quran_passages.py"),
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
        consumers=("retrieval/verse_lookup.py", "scripts/build_quran_close_verses.py",
                   "scripts/build_quran_passages.py"),
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
                   "retrieval/verse_lookup.py", "scripts/build_quran_close_verses.py"),
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
    "SURAH_SIMILARITY_JSON": Entry(
        bucket="derived",
        what="Intra-surah verse similarity, schema 2 (~3 MB): per surah its "
             "`unscored` ayahs, its `groups` of mutually close verses and, per "
             "ayah, at most K=10 neighbours of the SAME surah that pass both the "
             "syntactic gate (COARSE QAC word signatures — stem segments only: "
             "verb aspect + voice, noun subcategory, particle tag; no clitic, "
             "suffix, case or mood — compared by Levenshtein with the blocks "
             "re-orderable along the pair's word matching, `syn ≥ σ`) and the "
             "semantic gate (cross-encoder + E5 cosine + `lex`, the IDF Jaccard "
             "of the order-invariant content-word matching, `sem ≥ τ_sem`), each "
             "with its signals (`lex`, formerly `cov`) and the roots of its "
             "matched content words; a pair is stored only when that matching "
             "carries a positive mass. Consecutive ayahs are never stored. The "
             "`build` header records the models, K, M, weights, thresholds, the "
             "signature (`stem-coarse`), its measure (`levenshtein+block-reorder`), "
             "the lexical signal (`matching-idf-jaccard`), the matching's "
             "tie-break (`median-shift`) and the gold-set sha256.",
        origin="Built from VERSES_FINAL_JSON (Arabic text), the Qdrant collection "
               "(E5 verse vectors), MORPHOLOGY_JSON + ROOTS_RESOLVED_JSON (content "
               "roots, IDF), QAC_MORPHOLOGY_TXT (coarse syntactic signature from "
               "the stem segments, no treebank role; word tokens), "
               "WORD_FUNCTION_JSON (tool filter) and "
               "BAAI/bge-reranker-v2-m3, with the coarse element, the matching, "
               "`syn` and `lex` imported from scripts/closeness_core.py and the "
               "per-word tokens from scripts/build_quran_passages.py. Needs the "
               "backend STOPPED: embedded Qdrant takes an exclusive lock.",
        producer="scripts/build_surah_similarity.py",
        consumers=("retrieval/surah_similarity.py", "api/routers/surah_similarity.py",
                   "scripts/eval_surah_similarity.py"),
        regenerable=True,
        rebuild="python scripts/build_surah_similarity.py  (backend stopped; add "
                "--no-gold on a clone without the local-only tests/eval/ gold set)",
    ),
    "SURAH_SIMILARITY_CHECKPOINT_DIR": Entry(
        bucket="derived",
        what="Per-surah resume markers of the similarity build — not a dataset. "
             "Each file is reused only when its digest — header parameters, "
             "derived inputs, verse vectors and the sources of the builder and "
             "of the definitions it imports (closeness_core, the passage "
             "build's token rule) — matches the running build; a torn or stale "
             "file is rebuilt. "
             "Deleting the directory costs a full rebuild.",
        origin="Written by the similarity builder as it progresses.",
        producer="scripts/build_surah_similarity.py",
        consumers=("scripts/build_surah_similarity.py",),
        regenerable=True,
        rebuild="python scripts/build_surah_similarity.py  (backend stopped)",
    ),
    "QURAN_SIMILARITY_JSON": Entry(
        bucket="derived",
        what="Cross-surah verse similarity, schema 2 (est. <= 3 MB): the "
             "`unscored` verse refs and, per verse ref (`s:a`), at most K=10 "
             "neighbours from OTHER surahs that pass the same syntactic gate "
             "(Levenshtein over the coarse QAC signature with the blocks "
             "re-orderable along the pair's word matching, `syn >= sigma`; a "
             "longer signature of <= 3 elements needs syn = 1), "
             "semantic gate (`sem >= tau_sem`, dense percentile-ranked among the "
             "syntax survivors, `lex` the IDF Jaccard of the order-invariant "
             "content-word matching) and matched-mass rule (`Mw > 0`) as the "
             "intra-surah build, each with its signals (`lex`, formerly `cov`) "
             "and the roots of its matched content words; each list keeps a "
             "neighbour only at >= rho x its best score. The syntactic gate runs "
             "behind two EXACT pre-filters, closeness_core's upper bounds of "
             "`syn` (length, coarse-element bag — both exact under any "
             "re-ordering). Only verses with at least one neighbour carry a "
             "list. The `build` header records scope, models, K, M, weights, "
             "thresholds, the signature (`stem-coarse`), its measure "
             "(`levenshtein+block-reorder`), the lexical signal "
             "(`matching-idf-jaccard`), the tie-break (`median-shift`), the "
             "gold-set sha256 and, under `blind_sample_sha256`, the sha256 of "
             "the bytes of tests/eval/closeness_blind_v2.json (null when absent).",
        origin="Built from VERSES_FINAL_JSON (Arabic text), the Qdrant collection "
               "(E5 verse vectors), MORPHOLOGY_JSON + ROOTS_RESOLVED_JSON (content "
               "roots, IDF), QAC_MORPHOLOGY_TXT (coarse syntactic signature, word "
               "tokens), WORD_FUNCTION_JSON (tool filter) and "
               "BAAI/bge-reranker-v2-m3, with the parameters and pure helpers "
               "imported from scripts/build_surah_similarity.py, which takes the "
               "element, the measure, the matching and the bounds from "
               "scripts/closeness_core.py. Needs the backend STOPPED: embedded "
               "Qdrant takes an exclusive lock.",
        producer="scripts/build_quran_similarity.py",
        consumers=("scripts/build_quran_close_verses.py", "scripts/eval_quran_similarity.py",
                   "scripts/eval_closeness_blind.py"),
        regenerable=True,
        rebuild="python scripts/build_quran_similarity.py  (backend stopped; add "
                "--no-gold on a clone without the local-only tests/eval/ gold set)",
    ),
    "QURAN_SIMILARITY_CHECKPOINT_DIR": Entry(
        bucket="derived",
        what="Per-anchor-surah resume markers of the cross-surah similarity "
             "build — not a dataset. Each file holds the cross-encoded, gated "
             "pairs whose lower verse lies in one surah, and is reused only when "
             "its digest — header parameters, derived inputs, verse vectors and "
             "the sources of both builders and of the definitions they import "
             "(closeness_core, the passage build's token rule) — matches the "
             "running build; a torn or stale file is rebuilt. Deleting the "
             "directory costs a full rebuild.",
        origin="Written by the cross-surah similarity builder as it progresses.",
        producer="scripts/build_quran_similarity.py",
        consumers=("scripts/build_quran_similarity.py",),
        regenerable=True,
        rebuild="python scripts/build_quran_similarity.py  (backend stopped)",
    ),
    "QURAN_PASSAGES_JSON": Entry(
        bucket="derived",
        what="Cross-surah shared passages, schema 2: one entry per pair of "
             "verses of DIFFERENT surahs whose order-invariant matching (one "
             "token per QAC word, the stem segment's lemma, else the bare "
             "surface; content words by lemma, other words by identical token, "
             "a repeated token paired at the median shift of the uniquely "
             "matched words) holds an ACCEPTED region -- a window pair bounded "
             "by matched words, in any order, with k >= 6 identical-token "
             "pairs, k >= 0.75 x the longer window and >= 3 of them joining "
             "content words -- the largest accepted one being stored "
             "(order-invariant-closeness D6, version 2; version 1's best-scoring "
             "region and Smith-Waterman retired). Each entry holds both refs "
             "(lower surah first), both 1-based region windows, k and the "
             "matched content roots. The `build` header records the token, "
             "content-word, matching and region rules, the names `tie_break` "
             "(`median-shift`) and `passage` (`largest-accepted-region`), the "
             "thresholds and the gold-set sha256.",
        origin="Built from QAC_MORPHOLOGY_TXT (lemmas, stems, ROOT features), "
               "ROOTS_RESOLVED_JSON (canonical roots), MORPHOLOGY_JSON and "
               "WORD_FUNCTION_JSON (the content-word definition, shared with the "
               "similarity builds through scripts/closeness_core.py). No model and "
               "no Qdrant: it may run with the backend up.",
        producer="scripts/build_quran_passages.py",
        consumers=("scripts/build_quran_close_verses.py", "scripts/eval_quran_passages.py"),
        regenerable=True,
        rebuild="python scripts/build_quran_passages.py  (add --no-gold on a clone "
                "without the local-only tests/eval/ gold set)",
    ),
    "QURAN_CLOSE_VERSES_JSON": Entry(
        bucket="derived",
        what="The unified cross-surah relation «close verses», schema 3: the "
             "UNION of the pairs QURAN_SIMILARITY_JSON stores and the pairs "
             "QURAN_PASSAGES_JSON holds. Each pair: both refs (lower surah "
             "first), sim (the similarity score sem x syn -- stored, or computed "
             "ungated for a passage-only pair), pas (passage words / words of "
             "the shorter verse, 0 without a passage), score = 1 - (1-sim)(1-pas), "
             "`from`, the shared content roots, the passage's own k / wa / wb on "
             "a passage pair and, when it has one, its common part: the "
             "content edges of the shared order-invariant matching "
             "(scripts/closeness_core.py; content word = a root among the "
             "verse's content roots, not a tool occurrence) (m = "
             "[[p, q, lemma|root]]) and, per verse, a list of half-open character "
             "spans (one per run of coloured words) in its displayed "
             "text_ar_tashkil (Basmala stripped). The header records the rules "
             "under the core's names (signature `stem-coarse`, its measure "
             "`levenshtein+block-reorder`, the lexical signal "
             "`matching-idf-jaccard`, `tie_break` `median-shift`, `passage` "
             "`largest-accepted-region`), the sha256 of both input files, of "
             "both gold sets and, under `blind_sample_sha256`, of the BYTES of "
             "tests/eval/closeness_blind_v2.json (never read; null when absent) "
             "-- what scripts/eval_closeness_blind.py refuses to measure without.",
        origin="Composed from QURAN_SIMILARITY_JSON and QURAN_PASSAGES_JSON, with "
               "the verse vectors (embedded Qdrant), the cross-encoder, the QAC "
               "morphology, WORD_FUNCTION_JSON (tool occurrences are not content "
               "words) and WORD_INDEX_JSON for the spans; a passage-only pair's "
               "sim goes through the core's syn (Levenshtein over the coarse "
               "signatures, blocks re-ordered along the pair's matching) and "
               "that matching's lex. Build order: "
               "build_quran_similarity.py -> build_quran_passages.py -> "
               "build_quran_close_verses.py. Needs the backend STOPPED: embedded "
               "Qdrant takes an exclusive lock.",
        producer="scripts/build_quran_close_verses.py",
        consumers=("retrieval/quran_close_verses.py", "api/routers/quran_similarity.py",
                   "scripts/eval_quran_close_verses.py", "scripts/eval_closeness_blind.py"),
        regenerable=True,
        rebuild="python scripts/build_quran_close_verses.py  (backend stopped; add "
                "--no-gold on a clone without the local-only tests/eval/ gold sets)",
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
