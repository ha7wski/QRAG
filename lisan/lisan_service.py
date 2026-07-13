"""
lisan_service.py — The "Lisan Analysis" pipeline.

Given an Arabic word, resolve its triconsonantal root (via the existing QAC
resolver — reused, never reinvented), read the interpretive meaning of each root
letter IN SEQUENCE from the letter lexicon, and synthesize them (via the shared
LLM_PROVIDER abstraction) into one coherent reading of the root's core sense.

Everything here is an INTERPRETIVE sound-symbolism heuristic, NOT lexicography;
the disclaimer travels in every response. The QAC resolver stays primary: a root
is `root_source == "qac"` unless it could only be reached by the gated stemmer
fallback (`QAC_STEMMER_FALLBACK=1`), in which case it is flagged `"fallback"`.

Pure logic only — the FastAPI layer lives in `api/routers/lisan.py`.
"""
from __future__ import annotations

import json
import sys
from itertools import permutations
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from ingestion.root_normalize import normalize_root  # noqa: E402
from retrieval.lexical_retriever import _clitic_alif_candidates  # noqa: E402
from lisan import letter_lexicon  # noqa: E402

# Requested-language → the name used in the synthesis prompt.
_LANG_NAMES = {"ar": "Arabic", "fr": "French", "en": "English"}

# Interpretive disclaimer, localized. English is the exact project-standard line.
DISCLAIMER = {
    "en": "Interpretive letter-symbolism, not established lexicography.",
    "fr": "Symbolisme interprétatif des lettres, non une définition lexicographique établie.",
    "ar": "قراءة رمزية تأويلية لدلالات الحروف، وليست تعريفًا معجميًّا ثابتًا.",
}

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

SYSTEM_PROMPT_TEMPLATE = (
    "You are a careful Arabic philology assistant. You are given a Quranic word, "
    "its triconsonantal root, and an ordered, interpretive meaning for each root "
    "letter (from a sound-symbolism framework, NOT a dictionary). Compose ONE "
    "short paragraph (3-5 sentences) in {LANGUAGE} that reads the root by chaining "
    "the letter meanings in order, then states the plausible core sense of the "
    "root and how the given word expresses it. Be explicit that this is an "
    "interpretive reading, not a lexical definition. Do not invent Quranic "
    "references. Do not add letters that are not in the root."
)


class LisanService:
    """Orchestrates normalize → resolve root → decompose → sequential read →
    LLM synthesis for the Lisan Analysis tab.

    `resolver` is the shared QAC-backed `LexicalRetriever` (reused, not rebuilt);
    `llm` is the shared `LLMClient` (LLM_PROVIDER abstraction). Both are injected
    so tests can stub them without touching disk, network, or a model.
    """

    def __init__(self, resolver, llm):
        self.lex = resolver
        self.llm = llm

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
    def decompose(root: str, lang: str = "ar") -> list[dict]:
        """Split a root into its letters and describe each (in order)."""
        return [letter_lexicon.describe(ch, lang) for ch in root]

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

    # ── LLM synthesis ─────────────────────────────────────────────────────
    def synthesize(
        self, word: str, root: str, letters: list[dict], lang: str = "ar"
    ) -> str:
        """Turn the ordered letter meanings into ONE coherent paragraph via the
        shared LLM_PROVIDER abstraction, in the requested language."""
        language = _LANG_NAMES.get(lang, "Arabic")
        system = SYSTEM_PROMPT_TEMPLATE.format(LANGUAGE=language)
        payload = {
            "word": word,
            "root": root,
            "ordered_letters": [
                {"letter": d["letter"], "meaning": d["meaning"]} for d in letters
            ],
        }
        user = json.dumps(payload, ensure_ascii=False)
        return self.llm.chat(system, [{"role": "user", "content": user}]).strip()

    # ── orchestration ─────────────────────────────────────────────────────
    def analyze(self, word: str, lang: str = "ar") -> dict:
        """Run the full pipeline and return the response object.

        When no root resolves, returns `root: None` with a helpful `message`
        (the caller returns 200, never 500)."""
        disclaimer = DISCLAIMER.get(lang, DISCLAIMER["en"])
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
                "ishtiqaq_akbar": [],
                "disclaimer": disclaimer,
                "sources": SOURCES,
                "message": (
                    f"Could not resolve an Arabic root for '{word}'. "
                    "It may be a proper noun or a word outside the Quranic corpus."
                ),
            }

        letters = self.decompose(root, lang)
        return {
            "word": word,
            "root": root,
            "root_source": resolved["root_source"],
            "letters": letters,
            "sequential_reading": self.sequential_reading(letters),
            "synthesis": self.synthesize(word, root, letters, lang),
            "ishtiqaq_akbar": self.ishtiqaq_akbar(root),
            "disclaimer": disclaimer,
            "sources": SOURCES,
            "message": None,
        }


if __name__ == "__main__":
    from generation.llm_client import LLMClient
    from retrieval.lexical_retriever import LexicalRetriever

    svc = LisanService(LexicalRetriever(), LLMClient())
    out = svc.analyze("رحمة", lang="en")
    print("root:", out["root"], "| source:", out["root_source"])
    for step in out["sequential_reading"]:
        print(f"  {step['index']}. {step['letter']} → {step['meaning']}")
    print("\nsynthesis:\n", out["synthesis"])
