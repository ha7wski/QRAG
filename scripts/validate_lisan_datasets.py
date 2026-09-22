#!/usr/bin/env python3
"""
validate_lisan_datasets.py — OFFLINE gate on the three curated Lisan datasets.

Checks `semantic_axes.json`, `root_cores.json` and `letter_senses.csv` against
the rules the constrained letter reading depends on, and prints a coverage
report. Exit code 0 when clean, 1 with every finding listed otherwise. No
network, no model, no LLM — every rule is a comparison between files already on
disk.

Why a validator rather than trust in curation: each of these rules guards a
failure that is SILENT in production.

  * A core keyed on the hamza-FOLDED spelling (the form `maqayis_asl.csv` is
    indexed on) matches ~0 of the 139 hamzated QAC roots. Nothing raises: the
    reading simply stops being constrained and looks like a normal uncovered
    root. Folding is how the seed script FINDS a Maqāyīs row, never how a key is
    stored (design D6).
  * A `verbatim` that has drifted from its Maqāyīs segment turns a citation into
    a paraphrase — and every letter of that root is then selected against words
    Ibn Fāris did not write.
  * A half-curated entry (empty `axes`, null `polarity`) makes a root look
    covered while it can never match a sense. The seed script leaves exactly
    those, so this is what stops an unfinished file shipping.
  * An uncited letter sense turns the selection step into a machine for
    producing whichever sense makes the root work. `linguistics/tahlil/
    citations.py` already refuses to publish generated prose it cannot cite;
    curated scholarship is held to the same gate — and PRESENCE is not enough:
    `page: "999-1000"` and `source: "حدسي"` are both non-empty and both
    worthless, so a citation is checked against the authority it names.
  * A core naming both members of an antonym pair conflicts with every sense at
    once, so the root reads entirely unmatched with nothing saying why.

Usage:
    python scripts/validate_lisan_datasets.py     # 0 = clean, 1 = findings

`validate()` is importable so `tests/test_lisan_datasets.py` drives these exact
rules instead of restating them — a second copy of a rule is a rule that can
disagree with itself.
"""
from __future__ import annotations

import hashlib
import re
import sys
from dataclasses import dataclass, replace
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from arabic_text import normalize_root  # noqa: E402
from linguistics.lisan import letter_lexicon, sense_selection  # noqa: E402
from quran_data import loaders  # noqa: E402
from quran_data.paths import LETTER_SENSES_CSV  # noqa: E402

# ── the closed enumerations both datasets are checked against ────────────────
POLARITIES = ("positive", "negative", "neutral")   # root_cores.json
POLES = ("positive", "negative", "neutral")        # letter_senses.csv
POSITION_ANY = "any"
SPECIFIC_POSITIONS = ("initial", "medial", "final")
POSITIONS = SPECIFIC_POSITIONS + (POSITION_ANY,)
CONFIDENCES = ("verified", "high", "summary")

# The 28 base consonants of the framework. Hamza seats (أ إ ؤ ئ آ ٱ) fold to ء
# and the bare alif ا is not a base consonant, so neither may appear as a row:
# a sense filed under a seat is unreachable through the lexicon's folding.
BASE_LETTERS = "ءبتثجحخدذرزسشصضطظعغفقكلمنهوي"
# Membership is asked of the SET, never of the string: `"" in BASE_LETTERS` and
# `"ءب" in BASE_LETTERS` are both True — `in` on a str is containment, so an
# empty `letter` cell and any adjacent run of letters walked straight through
# this gate. Such a row is invisible at both ends: the validator passed it and
# the lexicon files it under a key no letter ever resolves to.
BASE_LETTER_SET = frozenset(BASE_LETTERS)

# Tatweel (kashida): a display elongation, not a letter.
# `arabic_letter_semantics_hasan_abbas.json` spells hāʾ as «هـ», so an index of
# that file keyed on its raw `letter` answers nothing for «ه» and the two shipped
# hāʾ senses would be reported as uncitable. Stripped on the way in.
TATWEEL = "ـ"

# The letter-level authorities a sense may cite. Closed for the same reason the
# axis vocabulary is: `source` is otherwise free text, and «حدسي» ("intuitive")
# is non-empty. Ḥasan ʿAbbās is the only one the shipped dataset cites; adding
# Ibn Jinnī (or any other) is a curation decision that must land HERE, visibly,
# rather than appear one row at a time.
LETTER_SENSE_SOURCES = ("حسن عباس، خصائص الحروف العربية ومعانيها",)

# The only authority a semantic core may cite: cores come from one work, and
# `verbatim` is checked byte-for-byte against that work's own CSV.
CORE_SOURCES = ("ابن فارس، معجم مقاييس اللغة",)

# Sentinel joining several aṣl of one root inside a single `asl_text` cell (must
# match `scripts/build_maqayis_dataset.py::ASL_DELIM`). Declared here rather than
# imported from `linguistics/madar/maqayis_store.py` so this validator stays a
# standalone reader of files — exactly as that store re-declares it too.
ASL_DELIM = " ||| "

# Maqāyīs rows that carry no usable aṣl. A core for one of these would be an
# invention wearing Ibn Fāris' name.
UNUSABLE_ASL_STATUS = ("no_asl", "parse_uncertain")


# ── inputs ───────────────────────────────────────────────────────────────────
@dataclass(frozen=True)
class Datasets:
    """The five inputs every rule reads, as plain data.

    Held as a value object so a test can hand in a deliberately broken in-memory
    copy (`dataclasses.replace`) without writing a file to disk — the rules and
    the shipped files are then exercised by the same code.

    `root_keys` is the canonical QAC root vocabulary rather than the whole
    morphology index: the only question asked of it is membership, and a set
    keeps a broken copy cheap to build.
    """

    axes: dict                      # semantic_axes.json, whole document
    cores: dict                     # root_cores.json, whole document
    senses: list[dict]              # letter_senses.csv rows, in file order
    root_keys: frozenset[str]       # canonical QAC root keys (morphology.json)
    maqayis: dict[str, dict]        # root_normalized → Maqāyīs row
    authority_pages: dict[str, str]  # base letter → the pages Ḥasan ʿAbbās is cited at
    lock: dict                      # letter_senses.lock.json, whole document
    senses_bytes: bytes             # the RAW bytes the lock's digest is taken over

    @classmethod
    def load(cls) -> "Datasets":
        """Read the shipped files through the registry's cached loaders.

        Returns the loaders' own objects — nothing here mutates them. A caller
        building a broken copy must deep-copy the piece it breaks, or it would
        corrupt the process-wide cache for every later test.

        `senses_bytes` is the one input read off disk rather than through a
        loader, because the freeze is taken over the FILE, not over the parsed
        rows: a reformat that leaves every row equal still changes the sheet,
        and a curated dataset does not get reformatted by accident.
        """
        return cls(
            axes=loaders.semantic_axes(),
            cores=loaders.root_cores(),
            senses=loaders.letter_senses(),
            root_keys=frozenset(loaders.morphology()),
            maqayis={r["root_normalized"]: r for r in loaders.maqayis_asl()},
            authority_pages=_authority_pages(loaders.letter_semantics()),
            lock=loaders.letter_senses_lock(),
            senses_bytes=LETTER_SENSES_CSV.read_bytes(),
        )

    def with_(self, **changes) -> "Datasets":
        """A copy with some inputs swapped — the injection point for tests."""
        return replace(self, **changes)


@dataclass(frozen=True)
class Coverage:
    """Curated-core coverage, computed FROM THE SHIPPED FILES, never hardcoded.

    A hardcoded figure is a figure that stops being true on the first curation
    batch, and this one is the number the next batch starts from.
    """

    qac_roots: int          # canonical root keys in morphology.json
    curated_roots: int      # of those, roots holding ≥1 core
    curated_cores: int      # cores in total (a root may hold several)
    ceiling: int            # QAC roots with a `has_asl` Maqāyīs row (fold + geminate)
    ceiling_direct: int     # the same, fold only — the documented 1149

    @property
    def curated_share(self) -> float:
        return 100.0 * self.curated_roots / self.qac_roots if self.qac_roots else 0.0

    @property
    def ceiling_share(self) -> float:
        return 100.0 * self.ceiling / self.qac_roots if self.qac_roots else 0.0


# ── shared helpers ───────────────────────────────────────────────────────────
def _geminate_variants(root: str) -> list[str]:
    """Orthographic bridges between QAC's doubled geminate roots and Maqāyīs'
    contracted spelling: `اب` ↔ `ابب`. Empty for non-geminate shapes.

    Copied from `linguistics/madar/maqayis_store.py::_geminate_variants` rather
    than imported: this script must keep reading files without pulling a
    request-path package (and its caches) into a validation run. The two must
    agree — a root the store can reach but the validator cannot would be a core
    whose `verbatim` is never checked.
    """
    out: list[str] = []
    if len(root) == 2:                            # اب → ابب
        out.append(root + root[-1])
    elif len(root) == 3 and root[1] == root[2]:   # ابب → اب
        out.append(root[:2])
    return out


def maqayis_row(root_key: str, maqayis: dict[str, dict]) -> dict | None:
    """The Maqāyīs row for a CANONICAL QAC root key, or None.

    The CSV is keyed on the hamza-safe fold, the cores on the exact spelling, so
    the fold is applied here — to FIND the row, never to store a key.
    """
    folded = normalize_root(root_key)
    row = maqayis.get(folded)
    if row is not None:
        return row
    for cand in _geminate_variants(folded):
        row = maqayis.get(cand)
        if row is not None:
            return row
    return None


def asl_segments(row: dict) -> list[str]:
    """The individual aṣl of a Maqāyīs row, in order (same split as the store)."""
    text = row.get("asl_text") or ""
    return [s for s in text.split(ASL_DELIM) if s.strip()]


def _split_cell(value: str) -> list[str]:
    """Split a ';'-separated dataset cell, trimmed, empties dropped."""
    return [part.strip() for part in (value or "").split(";") if part.strip()]


def _text(value) -> str:
    """A CSV/JSON cell as trimmed text — `None` and a missing column read empty."""
    return (value or "").strip() if isinstance(value, (str, type(None))) else str(value)


def _axis_antonyms(axes_doc: dict) -> dict[str, str]:
    """`axis id → its declared antonym` («» when it declares none).

    Carried as one map rather than a bare id set because two rules need it: an
    unknown id is read off the keys, and a self-conflicting entry — one naming
    both poles of a pair — off the values.
    """
    return {
        _text(a.get("id")): _text(a.get("antonym"))
        for a in axes_doc.get("axes", [])
        if isinstance(a, dict) and _text(a.get("id"))
    }


def _authority_pages(semantics_doc: dict) -> dict[str, str]:
    """`base letter → the page range Ḥasan ʿAbbās is cited at` for that letter.

    Read from `arabic_letter_semantics_hasan_abbas.json`, the letter-level
    authority already registered in the manifest — so a sense's `page` can be
    checked against the chapter it claims to come from instead of merely being
    non-empty. Tatweel is stripped from the key: that file writes hāʾ as «هـ».
    """
    pages: dict[str, str] = {}
    for entry in semantics_doc.get("letters", []):
        if not isinstance(entry, dict):
            continue
        letter = _text(entry.get("letter")).replace(TATWEEL, "")
        dalala = entry.get("dalala_hasan_abbas") or {}
        page = _text(dalala.get("pages")) if isinstance(dalala, dict) else ""
        if letter and page:
            pages[letter] = page
    return pages


def _self_conflicting(axis_ids: list[str], antonyms: dict[str, str]) -> list[tuple[str, str]]:
    """The antonym pairs an entry names BOTH sides of, each pair reported once.

    Naming a pole and its opposite is not a richer tagging: the selection step
    rejects any sense that carries an axis opposed to the core's, so an entry
    holding both conflicts with everything — the root then reads entirely
    unmatched, with nothing in the response pointing at the dataset.
    """
    present = set(axis_ids)
    pairs = {
        (min(a, antonyms[a]), max(a, antonyms[a]))
        for a in present
        if antonyms.get(a) and antonyms[a] in present
    }
    return sorted(pairs)


# ── rule sets, one per file ──────────────────────────────────────────────────
def check_semantic_axes(axes_doc: dict) -> list[str]:
    """Unique ids, and `antonym` links that exist and are declared BOTH ways.

    Symmetry is not tidiness: the selection step distinguishes «no shared axis»
    from «an opposed axis» by looking the sense's axes up in the core's antonyms.
    A one-sided declaration makes that answer depend on which side is asked, so
    the same pair of axes reads as opposed in one direction and unrelated in the
    other.
    """
    findings: list[str] = []
    entries = axes_doc.get("axes")
    if not isinstance(entries, list) or not entries:
        return ["semantic_axes.json: `axes` is missing or empty"]

    antonyms: dict[str, str] = {}
    seen: set[str] = set()
    for i, axis in enumerate(entries):
        if not isinstance(axis, dict):
            findings.append(f"semantic_axes.json: entry #{i} is not an object")
            continue
        aid = _text(axis.get("id"))
        if not aid:
            findings.append(f"semantic_axes.json: entry #{i} has no `id`")
            continue
        if aid in seen:
            findings.append(f"semantic_axes.json: duplicate axis id «{aid}»")
        seen.add(aid)
        if not _text(axis.get("label_ar")):
            findings.append(f"semantic_axes.json: axis «{aid}» has an empty `label_ar`")
        if "antonym" in axis and _text(axis.get("antonym")):
            antonyms[aid] = _text(axis["antonym"])

    for aid, other in antonyms.items():
        if other not in seen:
            findings.append(
                f"semantic_axes.json: axis «{aid}» declares antonym «{other}», "
                "which is not a declared axis"
            )
        elif antonyms.get(other) != aid:
            findings.append(
                f"semantic_axes.json: one-sided antonym — «{aid}» names «{other}» "
                f"but «{other}» names «{antonyms.get(other) or 'nothing'}»"
            )
    return findings


def check_root_cores(cores_doc: dict, antonyms: dict[str, str], root_keys: frozenset[str],
                     maqayis: dict[str, dict]) -> list[str]:
    """Keys are canonical QAC roots; `verbatim` is byte-identical to its Maqāyīs
    segment; the citation names the right work and edition; axes and polarity are
    curated, not left at their seeded blanks."""
    findings: list[str] = []
    axis_ids = set(antonyms)
    roots = cores_doc.get("roots")
    if not isinstance(roots, dict):
        return ["root_cores.json: `roots` is missing or is not an object"]

    for key, cores in roots.items():
        # 1. The fold trap. A folded key resolves to no QAC root and degrades to
        #    «no core», which is indistinguishable from an uncurated root.
        if key not in root_keys:
            findings.append(
                f"root_cores.json: «{key}» is not a canonical QAC root key — keys "
                "must be the exact hamza-bearing spelling from morphology.json, "
                "not the folded form maqayis_asl.csv is indexed on"
            )

        if not isinstance(cores, list) or not cores:
            findings.append(f"root_cores.json: «{key}» holds no core list")
            continue

        # 2. The citation half, checked against its source rather than trusted.
        row = maqayis_row(key, maqayis)
        segments: list[str] = []
        if row is None:
            findings.append(
                f"root_cores.json: «{key}» has no Maqāyīs row, so its `verbatim` "
                "cannot be checked against a citation"
            )
        elif _text(row.get("asl_status")) in UNUSABLE_ASL_STATUS:
            findings.append(
                f"root_cores.json: «{key}» has a Maqāyīs row with asl_status "
                f"«{_text(row.get('asl_status'))}» — a root with no cited aṣl must be "
                "absent from the dataset, not present with an invented core"
            )
        else:
            segments = asl_segments(row)
            if len(segments) != len(cores):
                findings.append(
                    f"root_cores.json: «{key}» holds {len(cores)} core(s) against "
                    f"{len(segments)} aṣl segment(s) in maqayis_asl.csv — cores are "
                    "one per aṣl, in the same order, never merged"
                )

        for i, core in enumerate(cores):
            where = f"root_cores.json: «{key}» core #{i}"
            if not isinstance(core, dict):
                findings.append(f"{where} is not an object")
                continue

            verbatim = core.get("verbatim") or ""
            if i < len(segments) and verbatim != segments[i]:
                # Byte-for-byte: a normalized or trimmed comparison would let a
                # rewritten citation pass as Ibn Fāris' own words.
                findings.append(
                    f"{where}: `verbatim` does not match its maqayis_asl.csv "
                    f"segment byte-for-byte\n      stored : {verbatim!r}\n"
                    f"      source : {segments[i]!r}"
                )

            axes = core.get("axes")
            if not isinstance(axes, list) or not axes:
                findings.append(
                    f"{where}: empty `axes` — a seeded entry that was never curated "
                    "matches no sense and cannot constrain a reading"
                )
            else:
                for aid in axes:
                    if _text(aid) not in axis_ids:
                        findings.append(
                            f"{where}: unknown axis id «{_text(aid)}» (not in "
                            "semantic_axes.json)"
                        )
                for a, b in _self_conflicting([_text(x) for x in axes], antonyms):
                    findings.append(
                        f"{where}: names both «{a}» and its declared antonym «{b}» — "
                        "a core opposed to itself conflicts with every sense, so the "
                        "root reads unmatched with no visible cause"
                    )

            polarity = core.get("polarity")
            if polarity not in POLARITIES:
                findings.append(
                    f"{where}: `polarity` is {polarity!r}, expected one of "
                    f"{', '.join(POLARITIES)} — null is the seed's blank, never a value"
                )

            for field in ("gloss", "source"):
                if not _text(core.get(field)):
                    findings.append(f"{where}: `{field}` is empty")

            # The citation names a work and an edition, and both are checked
            # against the row the `verbatim` was taken from. Ibn Fāris' sentence
            # under Ḥasan ʿAbbās' name, or under an edition nobody printed, is a
            # citation that cannot be followed back.
            source = _text(core.get("source"))
            if source and source not in CORE_SOURCES:
                findings.append(
                    f"{where}: `source` is «{source}», not the work these cores are "
                    f"cited from ({', '.join(CORE_SOURCES)})"
                )
            if row is not None:
                edition = _text(core.get("edition"))
                expected = _text(row.get("edition"))
                if edition != expected:
                    findings.append(
                        f"{where}: `edition` is «{edition}», but its maqayis_asl.csv "
                        f"row carries «{expected}»"
                    )
    return findings


def check_letter_senses(rows: list[dict], antonyms: dict[str, str],
                        authority_pages: dict[str, str]) -> list[str]:
    """Every base letter readable, every sense identified, taggable, and cited at
    the page its own authority is registered at."""
    findings: list[str] = []
    axis_ids = set(antonyms)
    if not rows:
        return ["letter_senses.csv: file is empty"]

    seen: set[tuple[str, str]] = set()
    letters_with_rows: set[str] = set()
    for i, row in enumerate(rows):
        letter = _text(row.get("letter"))
        sense_id = _text(row.get("sense_id"))
        where = f"letter_senses.csv: row #{i + 2} «{letter}»/«{sense_id}»"  # +2: header + 1-based

        if letter not in BASE_LETTER_SET:
            findings.append(
                f"{where}: «{letter}» is not one of the 28 base letters — a sense "
                "filed under a hamza seat, the bare alif, an empty cell or a run of "
                "several letters is unreachable, since the lexicon looks a sense up "
                "by one folded base glyph"
            )
        else:
            letters_with_rows.add(letter)

        if not sense_id:
            findings.append(f"{where}: empty `sense_id`")
        elif (letter, sense_id) in seen:
            findings.append(
                f"{where}: duplicate `sense_id` within «{letter}» — ids are how a "
                "selection names the sense it chose"
            )
        seen.add((letter, sense_id))

        if not _text(row.get("gloss_ar")):
            findings.append(f"{where}: empty `gloss_ar`")

        axes = _split_cell(_text(row.get("axes")))
        if not axes:
            findings.append(
                f"{where}: empty `axes` — an untagged sense can never share an axis "
                "with a core, so it is dead weight the selection can never pick"
            )
        for aid in axes:
            if aid not in axis_ids:
                findings.append(
                    f"{where}: unknown axis id «{aid}» (not in semantic_axes.json)"
                )
        for a, b in _self_conflicting(axes, antonyms):
            findings.append(
                f"{where}: names both «{a}» and its declared antonym «{b}» — a sense "
                "opposed to itself is rejected against every core that shares either"
            )

        for field, allowed in (("pole", POLES), ("confidence", CONFIDENCES)):
            value = _text(row.get(field))
            if value not in allowed:
                findings.append(
                    f"{where}: `{field}` is «{value}», expected one of {', '.join(allowed)}"
                )

        # `position` is a SET, `;`-separated like `axes`: Ḥasan ʿAbbās states
        # «في الآخر والوسط» as ONE predicate over two positions, and splitting
        # that into two rows is what produced the sheet's only duplicate gloss.
        positions = _split_cell(_text(row.get("position")))
        for value in positions:
            if value not in POSITIONS:
                findings.append(
                    f"{where}: `position` names «{value}», expected one of "
                    f"{', '.join(POSITIONS)}"
                )
        if len(positions) != len(set(positions)):
            findings.append(f"{where}: `position` repeats a value")
        if POSITION_ANY in positions and len(positions) > 1:
            findings.append(
                f"{where}: `position` names «{POSITION_ANY}» beside a specific "
                "position — `any` already covers every one of them"
            )
        if set(positions) == set(SPECIFIC_POSITIONS):
            findings.append(
                f"{where}: `position` names all three specific positions; that is "
                f"«{POSITION_ANY}» written the long way, and only `any` is read as "
                "«the authority states no position»"
            )

        # The citation gate. Refusing an uncited sense is what keeps the curation
        # from being authored to fit whichever root the curator was looking at —
        # and presence alone does not refuse anything: `page: "0"` and
        # `source: "حدسي"` are both filled in. So the citation is checked against
        # the authority it names: the source must be one the project actually
        # cites, and the page must be the locus that authority is registered at
        # in `arabic_letter_semantics_hasan_abbas.json`.
        for field in ("source", "page"):
            if not _text(row.get(field)):
                findings.append(
                    f"{where}: empty `{field}` — a sense with no cited authority and "
                    "locus is refused"
                )

        source = _text(row.get("source"))
        if source and source not in LETTER_SENSE_SOURCES:
            findings.append(
                f"{where}: `source` is «{source}», which is not one of the cited "
                f"letter-level authorities ({', '.join(LETTER_SENSE_SOURCES)})"
            )

        page = _text(row.get("page"))
        expected_page = authority_pages.get(letter)
        if expected_page is None:
            # Tolerated, not crashed: a letter the authority file does not cover
            # cannot be page-checked, and that gap is itself worth reporting.
            if letter in BASE_LETTER_SET:
                findings.append(
                    f"{where}: «{letter}» is absent from the letter-level authority "
                    "file, so `page` cannot be checked against it"
                )
        elif page and page != expected_page:
            findings.append(
                f"{where}: `page` is «{page}», but Ḥasan ʿAbbās is cited at "
                f"«{expected_page}» for «{letter}» — a page that points nowhere is a "
                "citation nobody can follow back"
            )

    for letter in BASE_LETTERS:
        if letter not in letters_with_rows:
            findings.append(
                f"letter_senses.csv: base letter «{letter}» has no sense row"
            )
    return findings


# ── coverage ─────────────────────────────────────────────────────────────────
SEMVER = re.compile(r"^\d+\.\d+\.\d+$")

# Every history entry must carry all four. `source` is the load-bearing one: a
# letter changes because an authority says so, never because a root failed to
# match — so a version whose reason cannot name a source is exactly the edit
# this freeze exists to catch.
HISTORY_FIELDS = ("version", "date", "reason", "source")


def check_letter_senses_lock(lock: dict, senses_bytes: bytes,
                             rows: list[dict]) -> list[str]:
    """The freeze on `letter_senses.csv`: the sheet did not move, or the version did.

    Root curation runs against a FIXED letter sheet. The failure this guards is
    not a crash, it is a method failure: a curator meets a root that matches
    nothing, adds a sense to a letter, and the root now "works" — which proves
    nothing, because the evidence was written to fit the conclusion. That is the
    circular curation R1 names, and it leaves no trace in the data. A digest
    over the file turns it into a red validator.

    The rule is not «never change a letter». It is «change it through a new
    version, justified by a letter-level authority» — so the check is against
    the lock's own history, not against immutability.
    """
    findings: list[str] = []
    if not isinstance(lock, dict) or not lock:
        return ["letter_senses.lock.json: missing or not an object"]

    version = _text(lock.get("version"))
    if not SEMVER.match(version):
        findings.append(
            f"letter_senses.lock.json: `version` «{version}» is not MAJOR.MINOR.PATCH"
        )

    declared = _text(lock.get("sha256")).lower()
    actual = hashlib.sha256(senses_bytes).hexdigest()
    if not declared:
        findings.append("letter_senses.lock.json: no `sha256`")
    elif declared != actual:
        findings.append(
            f"letter_senses.csv has changed under a frozen version: the lock "
            f"declares sha256 {declared[:12]}… and the file hashes to "
            f"{actual[:12]}…. Either revert the edit, or bump `version` and add "
            f"a `history` entry naming the letter-level authority that "
            f"justifies it — never a root that did not match."
        )

    for field, expected in (("rows", len(rows)),
                            ("letters", len({_text(r.get("letter")) for r in rows}))):
        if field in lock and lock.get(field) != expected:
            findings.append(
                f"letter_senses.lock.json: `{field}` says {lock.get(field)}, "
                f"the sheet holds {expected}"
            )

    target = _text(lock.get("target"))
    if target and not target.endswith("letter_senses.csv"):
        findings.append(
            f"letter_senses.lock.json: `target` «{target}» is not letter_senses.csv"
        )

    history = lock.get("history")
    if not isinstance(history, list) or not history:
        findings.append("letter_senses.lock.json: `history` is missing or empty")
        return findings

    seen: set[str] = set()
    for i, entry in enumerate(history):
        if not isinstance(entry, dict):
            findings.append(f"letter_senses.lock.json: history #{i} is not an object")
            continue
        for field in HISTORY_FIELDS:
            if not _text(entry.get(field)):
                findings.append(
                    f"letter_senses.lock.json: history #{i} has no `{field}`"
                )
        hver = _text(entry.get("version"))
        if hver and hver in seen:
            findings.append(
                f"letter_senses.lock.json: history declares version «{hver}» twice"
            )
        seen.add(hver)

    # The current version must be the one the history ends on. A bumped version
    # with no entry behind it is a freeze whose reason was never written down.
    last = history[-1] if isinstance(history[-1], dict) else {}
    if version and _text(last.get("version")) != version:
        findings.append(
            f"letter_senses.lock.json: `version` is «{version}» but the last "
            f"history entry is «{_text(last.get('version'))}» — every version "
            f"carries its own reason and source"
        )
    if declared and _text(last.get("sha256")).lower() not in ("", declared):
        findings.append(
            "letter_senses.lock.json: the last history entry's `sha256` "
            "disagrees with the top-level one"
        )
    return findings


# ── the method indicator (rule 4) ────────────────────────────────────────────
@dataclass(frozen=True)
class MethodHealth:
    """Is the method still falsifiable as coverage grows?

    Two rates, read off the CURATED SET by running the real selection step:

      * `unmatched` — letter slots no sense was eligible for. Expected to be
        HIGH while coverage is thin, and it is a healthy number: it is the
        system declining to assert.
      * `divergence` — readings whose aggregate pole contradicts their own
        core's polarity. This is the falsifiability probe. The guard detects
        and never corrects, so a rate stuck at 0 % once the curated set is
        large means the letter senses agree with every core they meet — which
        is what curating letters to fit roots would look like from the outside.

    `barren` names the READINGS where no letter matched at all — labelled
    `root#n` when a root holds several aṣl, because the unit is the reading and
    not the root: ظلم's «خلاف الضياء والنور» matches nothing while its second
    aṣl matches ظ, and rolling the two up to the root would hide exactly the
    result this list exists to record. These are results, not failures, and
    naming them is how they get consigned instead of quietly prompting someone
    to edit a letter until they go away.
    """

    roots: int
    readings: int
    letter_slots: int
    unmatched_slots: int
    diverging_readings: int
    barren: tuple[str, ...]

    # Below this, a 0 % divergence rate says nothing either way — five roots
    # cannot exercise a contradiction. Past it, silence becomes a finding.
    FALSIFIABILITY_THRESHOLD = 50

    @property
    def unmatched_rate(self) -> float:
        return 100.0 * self.unmatched_slots / self.letter_slots if self.letter_slots else 0.0

    @property
    def divergence_rate(self) -> float:
        return 100.0 * self.diverging_readings / self.readings if self.readings else 0.0

    @property
    def verdict(self) -> str:
        """One line on whether the numbers can still be believed."""
        if self.roots < self.FALSIFIABILITY_THRESHOLD:
            return (f"not yet testable — {self.roots} curated roots, the probe needs "
                    f"{self.FALSIFIABILITY_THRESHOLD}")
        if self.diverging_readings == 0:
            return (f"NOT FALSIFIABLE — {self.roots} roots and the divergence guard has "
                    f"never fired. Audit the letter senses for curation written to fit "
                    f"the cores (R1).")
        return "testable — the guard has fired on real data"


def method_health(cores_doc: dict, antonyms: dict[str, str]) -> MethodHealth:
    """Run the real selection step over every curated root and count.

    Uses the production modules rather than a reimplementation: a metric
    computed by a second copy of the algorithm measures the copy.
    """
    roots = cores_doc.get("roots") if isinstance(cores_doc.get("roots"), dict) else {}
    readings = slots = unmatched = diverging = 0
    barren: list[str] = []

    for root, cores in sorted(roots.items()):
        if not isinstance(cores, list) or not cores:
            continue
        letters = [letter_lexicon.describe(ch) for ch in root]
        for n, core in enumerate(cores):
            if not isinstance(core, dict) or not core.get("axes") or not core.get("polarity"):
                continue                      # half-curated: never served, never counted
            read = sense_selection.select_for_root(letters, core["axes"], antonyms)
            readings += 1
            slots += len(read)
            hit = sum(1 for r in read if r.get("selected"))
            unmatched += len(read) - hit
            if not hit:
                barren.append(root if len(cores) == 1 else f"{root}#{n}")
            if sense_selection.detect_divergence(read, _text(core.get("polarity"))):
                diverging += 1

    return MethodHealth(
        roots=len([k for k, v in roots.items() if isinstance(v, list) and v]),
        readings=readings,
        letter_slots=slots,
        unmatched_slots=unmatched,
        diverging_readings=diverging,
        barren=tuple(barren),
    )


def coverage(cores_doc: dict, root_keys: frozenset[str],
             maqayis: dict[str, dict]) -> Coverage:
    """Curated coverage and the Maqāyīs ceiling, both read off the shipped files.

    The ceiling is what curation can ever reach: a root Ibn Fāris gives no aṣl
    for gets no core, by design. It is counted with the same fold + geminate
    lookup a core's `verbatim` check uses, so the two figures describe the same
    set of reachable rows; the fold-only figure is reported beside it because it
    is the 1149 quoted in the design.
    """
    roots = cores_doc.get("roots") if isinstance(cores_doc.get("roots"), dict) else {}
    curated = [k for k, v in roots.items() if k in root_keys and isinstance(v, list) and v]
    cores_total = sum(len(roots[k]) for k in curated)

    ceiling = 0
    ceiling_direct = 0
    for key in root_keys:
        direct = maqayis.get(normalize_root(key))
        if direct is not None and _text(direct.get("asl_status")) == "has_asl":
            ceiling_direct += 1
        row = maqayis_row(key, maqayis)
        if row is not None and _text(row.get("asl_status")) == "has_asl":
            ceiling += 1

    return Coverage(
        qac_roots=len(root_keys),
        curated_roots=len(curated),
        curated_cores=cores_total,
        ceiling=ceiling,
        ceiling_direct=ceiling_direct,
    )


# ── entry points ─────────────────────────────────────────────────────────────
def validate(data: Datasets | None = None) -> list[str]:
    """Every finding across the three datasets, in file order. Empty == clean."""
    data = data or Datasets.load()
    antonyms = _axis_antonyms(data.axes)
    return [
        *check_semantic_axes(data.axes),
        *check_root_cores(data.cores, antonyms, data.root_keys, data.maqayis),
        *check_letter_senses(data.senses, antonyms, data.authority_pages),
        *check_letter_senses_lock(data.lock, data.senses_bytes, data.senses),
    ]


def report(findings: list[str], cov: Coverage, lock: dict,
           health: MethodHealth) -> None:
    """Print the coverage summary, and the findings when there are any.

    The summary prints even on a clean run: coverage is the number the next
    curation batch starts from, so a clean validator that says nothing would
    leave it to be guessed. The method block prints for the same reason — the
    two rates are only meaningful as a TREND across curation batches, so each
    run has to leave its figures behind.
    """
    print("=" * 64)
    print("LISAN DATASETS — validation report")
    print("=" * 64)
    print(f"  QAC roots            : {cov.qac_roots}")
    print(f"  with a curated core  : {cov.curated_roots} "
          f"({cov.curated_share:.1f}% of QAC roots, {cov.curated_cores} cores)")
    print(f"  Maqāyīs ceiling      : {cov.ceiling} "
          f"({cov.ceiling_share:.1f}%) QAC roots with a has_asl row "
          f"[{cov.ceiling_direct} without the geminate bridge]")
    print(f"  letter sheet         : FROZEN at v{_text(lock.get('version')) or '?'} "
          f"({lock.get('rows', '?')} senses / {lock.get('letters', '?')} letters, "
          f"since {_text(lock.get('frozen_on')) or '?'})")

    print()
    print("  ── method indicator (roots are curated against the frozen sheet) ──")
    print(f"  unmatched   : {health.unmatched_rate:5.1f}%  "
          f"({health.unmatched_slots}/{health.letter_slots} letter slots)")
    print(f"  divergence  : {health.divergence_rate:5.1f}%  "
          f"({health.diverging_readings}/{health.readings} readings)")
    print(f"  verdict     : {health.verdict}")
    if health.barren:
        print(f"  no letter matched, recorded as-is ({len(health.barren)} reading(s)): "
              + "، ".join(health.barren))

    if not findings:
        print("\n  findings: none — the three datasets are consistent.")
    else:
        print(f"\n  findings: {len(findings)}")
        for f in findings:
            print(f"    - {f}")
    print("=" * 64)


def main() -> int:
    data = Datasets.load()
    findings = validate(data)
    report(
        findings,
        coverage(data.cores, data.root_keys, data.maqayis),
        data.lock,
        method_health(data.cores, _axis_antonyms(data.axes)),
    )
    return 1 if findings else 0


if __name__ == "__main__":
    raise SystemExit(main())
