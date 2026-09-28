"""
lisan_service.py — The "Lisan Analysis" pipeline (Arabic-only, LLM-free).

The order is the whole point: **word → root → attested core(s) → per-letter
sense selection constrained by the core → synthesis**. The letter senses are
read only after a core is in hand.

The former pipeline ran the other way: it read ONE frozen gloss per letter and
chained them. Nothing in that path knew what the root meant, so nothing could
prefer one sense of a letter over another — there was only one on file. On
`خ-ي-ر` it produced «القذارة والخشونة والخواء … فساد» against Ibn Fāris'
«أصله العطف والميل». The same `خ` is legitimately «خشونة/خبث» in `خ-ب-ث`
(«أصل واحد يدل على خلاف الطيب») and legitimately «رقة/نضارة» in `خ-ي-ر`; a design
that cannot produce both readings from the same letter has not fixed anything.

Three rules this module exists to enforce:

  * **No silent fallback.** A root with no core gets `constrained: False`, an
    Arabic warning and the senses as an INVENTORY — never a composed paragraph.
    A letter with no eligible sense is `unmatched` and asserts nothing. There is
    no flag restoring the old concatenation, because a flag that restores the
    `خ-ي-ر` bug is the thing this change removes.
  * **One reading per core, never a blend.** Pooling ظلم's two aṣl («خلاف الضياء
    والنور» and «وضع الشيء غير موضعه تعديا») would make almost any sense eligible
    and rebuild the undifferentiated reading being removed.
  * **The guard detects, never corrects.** It runs on the FINISHED selection and
    returns a verdict; it is handed no way to re-rank.

No model anywhere: the synthesis was de-LLM'd once already (fluent prose
contradicting the attested sense), and a model in the *selection* step would
rebuild that failure one layer down, where it is harder to see.

Pure logic only — the FastAPI layer lives in `api/routers/lisan.py`.
"""
from __future__ import annotations

import sys
from itertools import permutations
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from arabic_text import normalize_root  # noqa: E402
from retrieval.lexical_retriever import clitic_alif_candidates  # noqa: E402
from linguistics.lisan import letter_lexicon, sense_selection  # noqa: E402
from linguistics.lisan.root_core_store import RootCoreStore  # noqa: E402
from linguistics.lisan.synthesis_template import render_synthesis  # noqa: E402
from linguistics.madar.maqayis_store import MaqayisStore  # noqa: E402

# Interpretive disclaimer (Arabic — the feature is Arabic-only).
DISCLAIMER = "قراءة رمزية تأويلية لدلالات الحروف، وليست تعريفًا معجميًّا ثابتًا."

# ── why there is no core, and whose silence it is ────────────────────────
#
# «No core» has THREE causes and they are not interchangeable. The page used to
# state one sentence for all of them — «لم يُسجَّل لهذا الجذر أصلٌ مُثبَتٌ في
# مقاييس اللغة» — which reads as «Ibn Fāris gives no aṣl for this root». For
# حرب that is simply false: he gives THREE («أحدها السلب، والآخر دويبة، والثالث
# بعض المجالس»), and محراب belongs to the third. The sentence was lending him a
# silence that is ours.
#
# The rule, and it is asymmetric on purpose: the project may report its OWN
# gap freely, and may report Ibn Fāris' silence only where the dataset
# positively records it (`asl_status == "no_asl"`, 14 roots). Absence of a row
# is absence of evidence — our extraction has gaps — so it falls to the
# project's side. When in doubt, the silence is ours.
CORE_STATUS_NOT_CURATED = "not_curated"        # he states an aṣl; we have not transcribed it
CORE_STATUS_NOT_RECORDED = "not_recorded"      # nothing on record here, and we claim nothing about him
CORE_STATUS_NO_ASL_IN_SOURCE = "no_asl_in_source"  # his entry itself formulates no aṣl

_INVENTORY_TAIL = (
    "فلا تُبنى عليه قراءةٌ مقيَّدة لحروفه. "
    "وما يلي جردٌ لمعاني حروفه كما وردت عند أصحابها، غيرُ مقيَّدٍ بأصلٍ ولا مختارٍ منه شيء."
)

NO_CORE_WARNINGS = {
    CORE_STATUS_NOT_CURATED: (
        "لهذا الجذر أصلٌ مذكورٌ في «مقاييس اللغة»، غير أنه لم يُسجَّل بعدُ في هذا المشروع، "
        + _INVENTORY_TAIL
    ),
    CORE_STATUS_NOT_RECORDED: (
        "لم يُسجَّل في هذا المشروع أصلٌ لهذا الجذر، وليس في ذلك نفيٌ لِما ذكره ابن فارس، "
        + _INVENTORY_TAIL
    ),
    CORE_STATUS_NO_ASL_IN_SOURCE: (
        "لم يذكر ابن فارس لهذا الجذر أصلًا في «مقاييس اللغة»، "
        + _INVENTORY_TAIL
    ),
}

# Source attributions surfaced in the response (framework, not our claim).
SOURCES = {
    "abbas": (
        "حسن عباس، خصائص الحروف العربية ومعانيها "
        "(إطارٌ في رمزية أصوات الحروف)."
    ),
    "ibn_faris": (
        "ابن فارس، معجم مقاييس اللغة (أصول الجذور المُثبَتة)."
    ),
    "ibn_jinni": (
        "ابن جنّي، الخصائص (الاشتقاق الأكبر؛ محاكاة أصوات الحروف)."
    ),
}


class LisanService:
    """Orchestrates normalize → resolve root → cores → constrained per-letter
    selection → deterministic Arabic synthesis → guard, for the Lisan tab.

    `resolver` is the shared QAC-backed `LexicalRetriever` (reused, not rebuilt);
    it is injected so tests can stub it without touching disk or network, and it
    is also what canonicalizes a root before the core lookup — `root_cores.json`
    is keyed on the EXACT, hamza-bearing spelling, and a lookup by the folded
    form would silently find nothing and degrade to «no core».

    `core_store` is injectable for the same reason: a test can hand it a
    hand-built core set and never read `data/`.
    """

    def __init__(self, resolver, core_store=None, maqayis=None, lookup=None):
        self.lex = resolver
        self.cores = core_store or RootCoreStore(resolver=resolver)
        # The ألفاظ and their counts come from the SAME object «الكلمة في الآيات»
        # uses, so the two pages cannot report different figures for one root —
        # see `occurrences`. Injected by the router (the API already builds one at
        # startup); built on first use otherwise, never at import, because it
        # opens the lemma and proper-noun indexes.
        self._lookup = lookup
        # Read-only, and ONLY to tell «Ibn Fāris says nothing» apart from «we
        # have not transcribed him yet» — never to build a core. A core is
        # curated (gloss, axes, polarity are readings of the citation); an aṣl
        # lifted straight out of the CSV would be an uncurated core wearing a
        # curated one's clothes, which is exactly what `_is_curated` refuses.
        self.maqayis = maqayis if maqayis is not None else MaqayisStore()

    @property
    def lookup(self):
        """The shared `VerseLookup`, built on demand when none was injected."""
        if self._lookup is None:
            from retrieval.verse_lookup import VerseLookup

            self._lookup = VerseLookup(retriever=self.lex)
        return self._lookup

    # ── normalization ─────────────────────────────────────────────────────
    @staticmethod
    def normalize(word: str) -> str:
        """Strip diacritics/tatweel and fold hamza SEATS only. Never deletes a
        hamza — reuses the project's root-safe `normalize_root` (bare `ء` kept)."""
        return normalize_root(word)

    # ── whose silence is it? ──────────────────────────────────────────────
    def core_status(self, root: str) -> str:
        """Why this root has no curated core — the project's gap, or Ibn Fāris'.

        Only `no_asl` lets us speak for him: that status means the entry was
        found, read, and formulates no aṣl. Everything else — a `has_asl` row we
        have not transcribed, a row our parser could not read, or no row at all
        — is the project's own silence and is reported as such.

        `parse_uncertain` deliberately falls to `not_recorded` rather than
        `not_curated`: we know his entry exists but not that it yields an aṣl,
        so claiming «he states one» would be as much of an invention as claiming
        he states none.
        """
        entry = self.maqayis.lookup(root)          # re-normalizes the key itself
        if entry is None:
            return CORE_STATUS_NOT_RECORDED
        if entry.asl_status == "has_asl":
            return CORE_STATUS_NOT_CURATED
        if entry.asl_status == "no_asl":
            return CORE_STATUS_NO_ASL_IN_SOURCE
        return CORE_STATUS_NOT_RECORDED

    # ── root resolution (QAC primary, gated fallback flagged) ─────────────
    def resolve_root(self, word: str) -> dict:
        """Resolve `word` to a single root via the existing QAC resolver.

        Returns `{root, roots, root_source}`:
          - `root_source == "qac"`   → resolved from the manually-verified QAC
            corpus: the strict ladder (root-key → surface FORM → lemma) or, if
            that misses, its clitic-/alif-stripped retries (peeling a leading
            `ال`, folding a plene alif). Both are QAC-backed, no stemmer.
          - `root_source == "fallback"` → only reachable via the gated legacy
            stemmer (`QAC_STEMMER_FALLBACK=1`); flagged so the UI can badge it.
          - `root is None` → nothing resolved.

        Mirrors the sibling "Word in Verses" lookup (strict → lenient QAC), so a
        user typing `الكتاب` / `السماوات` resolves, while the stemmer stays gated.
        """
        w = self.normalize(word)
        if not w:
            return {"root": None, "roots": [], "root_source": None}
        # 1. Strict QAC ladder — the primary, most-trusted path.
        qac_roots = self.lex._ladder(w)
        if qac_roots:
            return {"root": qac_roots[0], "roots": qac_roots, "root_source": "qac"}
        # 2. Lenient QAC retries (clitic-stripped / plene→defective alif), still
        #    QAC-backed — the ladder is re-run on each candidate stem, never the
        #    stemmer. This is why it stays labeled "qac".
        for stem in clitic_alif_candidates(w):
            retried = self.lex._ladder(stem)
            if retried:
                return {"root": retried[0], "roots": retried, "root_source": "qac"}
        # 3. Gated fallback: resolve_roots applies the legacy stemmer ONLY when
        #    QAC_STEMMER_FALLBACK=1, so a non-empty result here is the fallback.
        fallback = self.lex.resolve_roots(word)
        if fallback:
            return {"root": fallback[0], "roots": fallback, "root_source": "fallback"}
        return {"root": None, "roots": [], "root_source": None}

    # ── decomposition ─────────────────────────────────────────────────────
    @staticmethod
    def decompose(root: str) -> list[dict]:
        """Split a root into its letters and describe each, in order.

        Each entry carries the letter's phonetics AND its whole sense bundle,
        unranked. Choosing among the bundle happens later, against a core — the
        lexicon does not know the root and must not pick."""
        return [letter_lexicon.describe(ch) for ch in root]

    @staticmethod
    def identities(root: str, letters: list[dict]) -> list[dict]:
        """The phonetic identity of each root letter — stable across every core,
        so it is published once instead of repeated inside each reading.

        Phonetics ONLY. `letter_lexicon.describe()` still returns the dataset's
        Ibn Jinnī sound-imitation note, and it is deliberately not forwarded: it
        is an unconstrained letter gloss («يوحي بالأشياء الخشنة الكريهة الجوفاء»
        for خ), and publishing it would leave the defect one render away.
        """
        n = len(letters)
        return [
            {
                "index": i + 1,
                "letter": d.get("letter", ""),   # describe() always supplies it
                "name": d.get("name", ""),
                "makhraj": d.get("makhraj", ""),
                "sifat": list(d.get("sifat", [])),
                "position": sense_selection.letter_position(i, n),
                "sense_count": len(d.get("senses", [])),
            }
            for i, d in enumerate(letters)
        ]

    # ── ishtiqaq al-akbar (Ibn Jinni permutations) ────────────────────────
    def ishtiqaq_akbar(self, root: str) -> list[dict]:
        """The permutations (taqālīb) of a 3-letter root — Ibn Jinni's
        "greater derivation": distinct orderings of the same letters are held to
        share a core sense. Interpretive; only produced for triliteral roots.

        Untouched by this change: it is the page's one remaining section that is
        not constrained by an attested aṣl."""
        if len(root) != 3:
            return []
        index = getattr(self.lex, "index", {}) or {}
        out: list[dict] = []
        seen: set[str] = set()
        for combo in permutations(root):
            form = "".join(combo)
            if form in seen:
                continue
            seen.add(form)
            attested = form in index
            out.append({
                "form": form,
                "gloss": "attested Quranic root" if attested else "",
            })
        return out

    # ── axis labels ───────────────────────────────────────────────────────
    def _axis_labels(self, *axis_id_groups) -> dict[str, str]:
        """id → Arabic label, for every axis named anywhere in the response.

        Published once at the top level so the UI renders axis NAMES without
        holding its own copy of the closed vocabulary — a second copy is a
        second thing to keep in sync."""
        labels = self.cores.axis_labels()
        wanted: set[str] = set()
        for group in axis_id_groups:
            wanted.update(group)
        return {a: labels[a] for a in sorted(wanted) if a in labels}

    @staticmethod
    def _axes_in(letter_readings: list[dict]) -> set[str]:
        """Every axis id a selection touched — selected AND discarded senses, so
        a rejected sense's axes are named too. The rejected members are the
        point of showing the bundle; leaving their axes as bare ids would hide
        why they lost."""
        out: set[str] = set()
        for reading in letter_readings:
            selected = reading.get("selected")
            if selected:
                out.update(selected.get("axes", []))
            out.update(reading.get("matched_axes", []))
            for dropped in reading.get("discarded", []):
                out.update((dropped.get("sense") or {}).get("axes", []))
        return out

    # ── orchestration ─────────────────────────────────────────────────────
    def occurrences(self, root: str) -> dict:
        """How often the root occurs in the corpus, in how many āyāt, and under
        which written forms — read from the object «دراسة الآية» reads.

        The ATTESTED layer of this page, and the reason it is published here at
        all: «تحليل اللسان» leads with what the corpus and Ibn Fāris record, and a
        root's occurrence list is the most solid thing the product holds about it.
        It used to reach the screen only through the concept engine's
        confrontation block, which made an attested fact depend on an
        experimental route staying up.

        It delegates to `VerseLookup.root_forms`, and that is the whole point: it
        used to read `morphology.json`'s `forms_found` through the resolver, which
        is a list of VOCALIZED surfaces and not of ألفاظ — رحم came out as 43 forms
        with `رَحْمَةً` / `رَحْمَةٍ` / `رَحْمَةُ` listed as three, against the 31 written forms
        «الكلمة في الآيات» shows for the same root. Two counts of one thing is a
        bug whichever is right, and the fix is not a second deduplication here: the
        grouping also strips the proclitics QAC declares and drops occurrences that
        serve as a grammatical tool, neither of which a fold over `forms_found`
        could reproduce. So this page stops counting and asks the page that counts.
        """
        if not root:
            return {"count": 0, "words": 0, "verse_ids": [], "forms": []}
        found = self.lookup.root_forms(root)
        return {
            "count": int(found["ayat"]),
            "words": int(found["words"]),
            "verse_ids": list(found["verse_ids"]),
            "forms": list(found["forms"]),
        }

    def analyze(self, word: str) -> dict:
        """Run the full pipeline and return the response object (Arabic-only).

        When no root resolves, returns `root: None` with a helpful `message`
        (the caller returns 200, never 500)."""
        resolved = self.resolve_root(word)
        root = resolved["root"]

        if root is None:
            return self._empty(
                word,
                # The same sentence the sibling service already returns
                # (linguistics/madar/madar_service.py). This is the most common
                # non-happy path on «تحليل اللسان», and it used to be a whole
                # English paragraph inside an otherwise Arabic screen.
                message=(
                    f"تعذّر إيجاد جذر عربي للكلمة «{word}». "
                    "قد تكون اسمَ علمٍ أو كلمةً خارج المعجم القرآني."
                ),
            )

        letters = self.decompose(root)
        identities = self.identities(root, letters)
        cores = self.cores.lookup(root)

        found = self.occurrences(root)
        base = {
            "word": word,
            "root": root,
            "root_source": resolved["root_source"],
            # The attested layer, published before anything interpretive is
            # composed from it.
            "occurrences": found["count"],
            "occurrence_words": found["words"],
            "occurrence_verses": found["verse_ids"],
            "forms": found["forms"],
            "letters": identities,
            "synthesis_source": "template",
            "ishtiqaq_akbar": self.ishtiqaq_akbar(root),
            "disclaimer": DISCLAIMER,
            "sources": SOURCES,
            "message": None,
        }

        # ── no core: the inventory path, labelled, with no synthesis ──────
        if not cores:
            status = self.core_status(root)
            # Position applies on THIS path too. The inventory is «the senses
            # of this letter», and a letter sits somewhere: showing the ر of
            # ح-ر-ب — a middle letter — «الثبات … في بدايات المصادر» and
            # «انتهاء الأحداث بحركة في أواخر المصادر» offers the reader two
            # senses their own authority scopes elsewhere.
            #
            # They are moved, not deleted. `out_of_position` keeps them on the
            # page with their positions visible, the same way `discarded` keeps
            # a rejected sense on the constrained path: this feature never
            # improves a reading by hiding what it dropped.
            total = len(letters)
            inventory = []
            for i, d in enumerate(letters):
                here = sense_selection.letter_position(i, total)
                applies, elsewhere = [], []
                for sense in d.get("senses", ()):
                    bucket = applies if sense_selection.applies_at(sense, here) else elsewhere
                    bucket.append(sense)
                # A DOMINANT position ranks, it does not exclude — so a sense the
                # author merely puts «mostly at the end» stays on the list for a
                # middle letter, below the ones that do fit. Sorting is stable, so
                # curator order survives inside each group.
                applies.sort(
                    key=lambda s: not sense_selection.fits_position(s, here))
                inventory.append({
                    "index": i + 1,
                    "letter": d.get("letter", ""),
                    "senses": applies,
                    "out_of_position": elsewhere,
                })
            inventory_axes = {
                axis
                for entry in inventory
                for key in ("senses", "out_of_position")
                for sense in entry[key]
                for axis in sense.get("axes", [])
            }
            return {
                **base,
                "constrained": False,
                "cores": [],
                "readings": [],
                "inventory": inventory,
                "axis_labels": self._axis_labels(inventory_axes),
                "core_status": status,
                "warning": NO_CORE_WARNINGS[status],
            }

        # ── constrained: one complete reading per core, never a blend ─────
        antonyms = self.cores.antonym_map()
        readings: list[dict] = []
        touched: set[str] = set()
        for core in cores:
            letter_readings = sense_selection.select_for_root(
                letters, core.get("axes", []), antonyms
            )
            # The guard runs on the FINISHED selection and is handed no sense
            # pool, so it cannot re-rank even by accident. Its verdict is
            # recorded beside the reading; the reading itself is not touched
            # again after this point.
            divergence = sense_selection.detect_divergence(
                letter_readings, core.get("polarity", "neutral")
            )
            readings.append({
                "core": core,
                "letters": letter_readings,
                "synthesis": render_synthesis(root, core, letter_readings, letters),
                "divergence": divergence,
            })
            touched |= self._axes_in(letter_readings) | set(core.get("axes", []))

        return {
            **base,
            "constrained": True,
            "cores": cores,
            "readings": readings,
            "inventory": [],
            "axis_labels": self._axis_labels(touched),
            "core_status": None,
            "warning": None,
        }

    def _empty(self, word: str, message: str | None) -> dict:
        """The rootless response. `constrained` is false here too: there is no
        root, so there is certainly no attested core to constrain anything."""
        return {
            "word": word,
            "root": None,
            "root_source": None,
            "constrained": False,
            "letters": [],
            "cores": [],
            "readings": [],
            "inventory": [],
            "axis_labels": {},
            "core_status": None,
            "warning": None,
            "synthesis_source": "template",
            "ishtiqaq_akbar": [],
            "disclaimer": DISCLAIMER,
            "sources": SOURCES,
            "message": message,
        }


if __name__ == "__main__":
    from retrieval.lexical_retriever import LexicalRetriever

    svc = LisanService(LexicalRetriever())
    for w in ("خير", "خبث", "كفر", "ظلم", "رحمة", "كتاب"):
        out = svc.analyze(w)
        print("=" * 70)
        print(f"{w} → root {out['root']} | constrained={out['constrained']}")
        if out["warning"]:
            print("  warning:", out["warning"])
        for reading in out["readings"]:
            print("  core:", reading["core"]["gloss"])
            for lr in reading["letters"]:
                sel = lr["selected"]
                print(f"    {lr['letter']} [{lr['selection_rule']}]",
                      sel["gloss_ar"] if sel else "—")
            print("  ", reading["synthesis"].replace("\n", "\n   "))
            if reading["divergence"]:
                print("  DIVERGENCE:", reading["divergence"]["message"])
