"""
lisan_service.py — The "Lisan Analysis" pipeline (Arabic-only, LLM-free).

Given an Arabic word, resolve its triconsonantal root (via the existing QAC
resolver — reused, never reinvented), read the interpretive meaning of each root
letter IN SEQUENCE from the letter lexicon, and compose them into one coherent
Arabic reading of the root — DETERMINISTICALLY, via `synthesis_template`.

The LLM synthesis step was removed: the local model (qwen2.5:7b) corrupted tokens
(a Latin fragment injected mid-word) and produced ungrounded prose that
contradicted the attested root sense. For a Quranic tool a fluent-but-false
reading is worse than a plain one, so the paragraph is now templated from the
letter data — no model, no network, no language branching. `generation/` and
other LLM consumers are untouched.

Everything here is an INTERPRETIVE sound-symbolism heuristic, NOT lexicography;
the disclaimer travels in every response. The QAC resolver stays primary: a root
is `root_source == "qac"` unless it could only be reached by the gated stemmer
fallback (`QAC_STEMMER_FALLBACK=1`), in which case it is flagged `"fallback"`.

Pure logic only — the FastAPI layer lives in `api/routers/lisan.py`.
"""
from __future__ import annotations

import sys
from itertools import permutations
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from ingestion.root_normalize import normalize_root  # noqa: E402
from retrieval.lexical_retriever import _clitic_alif_candidates  # noqa: E402
from lisan import letter_lexicon  # noqa: E402
from lisan.synthesis_template import render_synthesis  # noqa: E402

# Interpretive disclaimer (Arabic — the feature is Arabic-only).
DISCLAIMER = "قراءة رمزية تأويلية لدلالات الحروف، وليست تعريفًا معجميًّا ثابتًا."

# Source attributions surfaced in the response (framework, not our claim).
SOURCES = {
    "abbas": (
        "Hasan Abbas, Khaṣāʾiṣ al-Ḥurūf al-ʿArabiyya wa-Maʿānīhā "
        "(letter sound-symbolism framework)."
    ),
    "ibn_jinni": (
        "Ibn Jinnī, al-Khaṣāʾiṣ (al-ishtiqāq al-akbar; letter sound-imitation)."
    ),
}


class LisanService:
    """Orchestrates normalize → resolve root → decompose → sequential read →
    deterministic Arabic synthesis for the Lisan Analysis tab.

    `resolver` is the shared QAC-backed `LexicalRetriever` (reused, not rebuilt);
    it is injected so tests can stub it without touching disk or network. There
    is no LLM dependency any more — synthesis is a pure template.
    """

    def __init__(self, resolver):
        self.lex = resolver

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
        for stem in _clitic_alif_candidates(w):
            retried = self.lex._ladder(stem)
            if retried:
                return {"root": retried[0], "roots": retried, "root_source": "qac"}
        # 3. Gated fallback: resolve_roots applies the legacy stemmer ONLY when
        #    QAC_STEMMER_FALLBACK=1, so a non-empty result here is the fallback.
        fallback = self.lex.resolve_roots(word)
        if fallback:
            return {"root": fallback[0], "roots": fallback, "root_source": "fallback"}
        return {"root": None, "roots": [], "root_source": None}

    # ── decomposition + sequential reading ────────────────────────────────
    @staticmethod
    def decompose(root: str) -> list[dict]:
        """Split a root into its letters and describe each (in order), in Arabic."""
        return [letter_lexicon.describe(ch) for ch in root]

    @staticmethod
    def sequential_reading(letters: list[dict]) -> list[dict]:
        """The ordered chain of per-letter meanings (letter 1 → 2 → 3 …).

        This ordered attribution is the core of the feature: the root's sense is
        read as the letters' meanings taken in sequence."""
        return [
            {"index": i, "letter": d["letter"], "meaning": d["meaning"]}
            for i, d in enumerate(letters, start=1)
        ]

    # ── ishtiqaq al-akbar (Ibn Jinni permutations) ────────────────────────
    def ishtiqaq_akbar(self, root: str) -> list[dict]:
        """The permutations (taqālīb) of a 3-letter root — Ibn Jinni's
        "greater derivation": distinct orderings of the same letters are held to
        share a core sense. Interpretive; only produced for triliteral roots.

        `gloss` marks whether each permutation is itself an attested root in the
        morphology index (when available), otherwise left empty."""
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

    # ── deterministic synthesis ───────────────────────────────────────────
    @staticmethod
    def synthesize(word: str, root: str, letters: list[dict]) -> str:
        """Compose the ordered letter meanings into ONE Arabic paragraph,
        deterministically (no LLM). Delegates to the pure `render_synthesis`."""
        return render_synthesis(word, root, letters)

    # ── orchestration ─────────────────────────────────────────────────────
    def analyze(self, word: str) -> dict:
        """Run the full pipeline and return the response object (Arabic-only).

        When no root resolves, returns `root: None` with a helpful `message`
        (the caller returns 200, never 500)."""
        resolved = self.resolve_root(word)
        root = resolved["root"]

        if root is None:
            return {
                "word": word,
                "root": None,
                "root_source": None,
                "letters": [],
                "sequential_reading": [],
                "synthesis": "",
                "synthesis_source": "template",
                "ishtiqaq_akbar": [],
                "disclaimer": DISCLAIMER,
                "sources": SOURCES,
                "message": (
                    f"Could not resolve an Arabic root for '{word}'. "
                    "It may be a proper noun or a word outside the Quranic corpus."
                ),
            }

        letters = self.decompose(root)
        return {
            "word": word,
            "root": root,
            "root_source": resolved["root_source"],
            "letters": letters,
            "sequential_reading": self.sequential_reading(letters),
            "synthesis": self.synthesize(word, root, letters),
            "synthesis_source": "template",
            "ishtiqaq_akbar": self.ishtiqaq_akbar(root),
            "disclaimer": DISCLAIMER,
            "sources": SOURCES,
            "message": None,
        }


if __name__ == "__main__":
    from retrieval.lexical_retriever import LexicalRetriever

    svc = LisanService(LexicalRetriever())
    out = svc.analyze("رحمة")
    print("root:", out["root"], "| source:", out["root_source"])
    for step in out["sequential_reading"]:
        print(f"  {step['index']}. {step['letter']} → {step['meaning']}")
    print("\nsynthesis:\n", out["synthesis"])
