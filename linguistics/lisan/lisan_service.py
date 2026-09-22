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

# Interpretive disclaimer (Arabic — the feature is Arabic-only).
DISCLAIMER = "قراءة رمزية تأويلية لدلالات الحروف، وليست تعريفًا معجميًّا ثابتًا."

# Said out loud, never papered over. At most 1 149 of the 1 656 QAC roots can
# ever have a Maqāyīs core and the curated set starts far smaller, so this is a
# normal outcome for a large minority of roots — not an edge case.
NO_CORE_WARNING = (
    "لم يُسجَّل لهذا الجذر أصلٌ مُثبَتٌ في «مقاييس اللغة»، "
    "فلا تُبنى عليه قراءةٌ مقيَّدة لحروفه. "
    "وما يلي جردٌ لمعاني حروفه كما وردت عند أصحابها، غيرُ مقيَّدٍ بأصلٍ ولا مختارٍ منه شيء."
)

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

    def __init__(self, resolver, core_store=None):
        self.lex = resolver
        self.cores = core_store or RootCoreStore(resolver=resolver)

    # ── normalization ─────────────────────────────────────────────────────
    @staticmethod
    def normalize(word: str) -> str:
        """Strip diacritics/tatweel and fold hamza SEATS only. Never deletes a
        hamza — reuses the project's root-safe `normalize_root` (bare `ء` kept)."""
        return normalize_root(word)

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

        base = {
            "word": word,
            "root": root,
            "root_source": resolved["root_source"],
            "letters": identities,
            "synthesis_source": "template",
            "ishtiqaq_akbar": self.ishtiqaq_akbar(root),
            "disclaimer": DISCLAIMER,
            "sources": SOURCES,
            "message": None,
        }

        # ── no core: the inventory path, labelled, with no synthesis ──────
        if not cores:
            inventory = [
                {
                    "index": i + 1,
                    "letter": d.get("letter", ""),
                    "senses": list(d.get("senses", [])),
                }
                for i, d in enumerate(letters)
            ]
            inventory_axes = {
                axis
                for entry in inventory
                for sense in entry["senses"]
                for axis in sense.get("axes", [])
            }
            return {
                **base,
                "constrained": False,
                "cores": [],
                "readings": [],
                "inventory": inventory,
                "axis_labels": self._axis_labels(inventory_axes),
                "warning": NO_CORE_WARNING,
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
