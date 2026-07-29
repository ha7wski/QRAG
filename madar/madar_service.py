"""
madar_service.py — Orchestrates the *madār* (sourced lexical reading) pipeline.

Given an Arabic word:
  a. resolve its root via the SAME QAC resolver `lisan/` uses (reused, not
     rewritten — `LisanService.resolve_root`);
  b. collect the root's Quranic occurrences (a representative sample carrying
     surface + reference, plus the full ref list and true total);
  c. look up Ibn Fāris' cited aṣl in the offline Maqāyīs store;
  d. OPTIONALLY (env-gated) ask the local LLM to synthesize the pivot from
     ONLY those verified inputs, then void the output if it drifts out of
     Arabic (deterministic post-check);
  e. return a structured object that keeps the cited aṣl, the occurrences, and
     the generated synthesis in strictly separate fields.

No `lisan/` file is modified: the resolver and the optional letter-reading
bridge are reused through a `LisanService` built on the shared retriever.
"""
from __future__ import annotations

import os
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from indexing.text_normalize import normalize_search  # noqa: E402
from ingestion.root_normalize import normalize_root  # noqa: E402
from lisan.lisan_service import LisanService  # noqa: E402
from madar.maqayis_store import MaqayisStore  # noqa: E402
from madar.synthesis_prompt import SYSTEM_PROMPT, build_user_message  # noqa: E402

# Occurrences sampled for the surface/ref list AND fed to the LLM prompt. The
# full ref list + true count are always returned separately (cheap, "s:a" only).
OCC_SAMPLE = 30

SYNTHESIS_ENV = "MADAR_SYNTHESIS_ENABLED"

# Marked GENERATED, never presented as Ibn Fāris' text.
SYNTHESIS_DISCLAIMER = (
    "توليفة مُولَّدة آليًّا لبيان المدار، وليست نصًّا لابن فارس ولا نقلًا حرفيًّا عنه."
)

# Post-check: reject synthesis that leaks Latin letters or CJK (qwen drift).
_LATIN_RE = re.compile(r"[A-Za-z]")
_CJK_RE = re.compile(r"[　-鿿가-퟿]")


def _synthesis_enabled() -> bool:
    """LLM synthesis is OFF unless MADAR_SYNTHESIS_ENABLED=1 (mirrors the
    project's other opt-in quality toggles). The cited aṣl + occurrences stand
    on their own; the synthesis is an optional layer."""
    return os.getenv(SYNTHESIS_ENV, "0") == "1"


def _is_arabic_clean(text: str) -> bool:
    """True if `text` carries no Latin word-characters and no CJK — the same
    spirit as the LLM removal in `lisan` (a fluent-but-corrupted paragraph is
    worse than none). Arabic, digits, and punctuation are fine."""
    if not text or not text.strip():
        return False
    return not _LATIN_RE.search(text) and not _CJK_RE.search(text)


class MadarService:
    """Sourced-lexical (`madār`) analysis for the Madar tab.

    `resolver` is the shared QAC `LexicalRetriever`. `llm` is the shared
    `LLMClient` (reused; only used when synthesis is enabled). `lisan` reuses the
    letter-symbolism service for root resolution AND the optional convergence
    note; it is built on the same resolver, so nothing heavy is duplicated.
    """

    def __init__(self, resolver, llm=None, lisan: LisanService | None = None,
                 store: MaqayisStore | None = None):
        self.lex = resolver
        self.llm = llm
        self.lisan = lisan or LisanService(resolver=resolver)
        self.store = store or MaqayisStore()

    # ── occurrences ───────────────────────────────────────────────────────
    def _occurrences(self, root: str) -> dict:
        """Sampled occurrences (surface + ref + context) plus the full ref list
        and the true total, from the shared morphology index."""
        res = self.lex.retrieve_by_root(root, sample=OCC_SAMPLE)
        norm_forms = [nf for nf in (normalize_search(f) for f in res["forms"]) if nf]
        sample: list[dict] = []
        for v in res["verses"]:
            text = v.get("text_ar", "")
            sample.append({
                "surface": self._surface(text, norm_forms),
                "surah": v.get("surah_number"),
                "ayah": v.get("ayah_number"),
                "context": text,
            })
        return {
            "sample": sample,
            "verse_ids": res["verse_ids"],
            "count": res["occurrences_count"],
        }

    @staticmethod
    def _surface(text: str, norm_forms: list[str]) -> str:
        """Best-effort surface form present in a verse: the first whitespace
        token whose hamza-safe normalization contains one of the root's forms.
        Falls back to "" when nothing matches (still deterministic)."""
        for tok in text.split():
            ntok = normalize_search(tok)
            if ntok and any(nf in ntok for nf in norm_forms):
                return tok
        return ""

    # ── synthesis (optional, env-gated) ───────────────────────────────────
    def _synthesize(self, root: str, asl_text: str | None,
                    occ: dict) -> tuple[str | None, str | None]:
        """Return (synthesis, note). `synthesis` is None when disabled, the LLM
        is unavailable, or the output failed the Arabic post-check; `note`
        explains why so the caller can surface it."""
        if not _synthesis_enabled():
            return None, "التوليفة اللغوية معطّلة."
        if self.llm is None or not getattr(self.llm, "health", lambda: False)():
            return None, "التوليفة غير متاحة: نموذج اللغة غير جاهز."
        user = build_user_message(root, asl_text, occ["sample"], occ["count"])
        try:
            raw = self.llm.chat(SYSTEM_PROMPT, [{"role": "user", "content": user}])
        except Exception:  # pragma: no cover — network/runtime failure
            return None, "التوليفة غير متاحة: تعذّر توليد النص."
        text = (raw or "").strip()
        if not _is_arabic_clean(text):
            return None, "التوليفة غير متاحة: النص المولَّد لم يكن عربيًّا خالصًا."
        return text, None

    # ── convergence bridge with lisan (optional, descriptive) ─────────────
    def _convergence(self, root: str, asl_text: str | None) -> str | None:
        """A DESCRIPTIVE, hedged note on whether `lisan`'s letter-symbolism
        reading shares vocabulary with Ibn Fāris' aṣl — never a strong claim.
        None when either side is missing or nothing is shared."""
        if not asl_text:
            return None
        try:
            letters = self.lisan.decompose(root)
        except Exception:  # pragma: no cover
            return None
        meanings = " ".join(d.get("meaning", "") for d in letters)
        shared = _shared_content_words(asl_text, meanings)
        if not shared:
            return None
        joined = "، ".join(sorted(shared))
        return (
            "ملاحظة وصفية (غير قطعية): تلتقي القراءة الرمزية لحروف الجذر مع أصل "
            f"ابن فارس في نحو: {joined}."
        )

    # ── orchestration ─────────────────────────────────────────────────────
    def analyze(self, word: str) -> dict:
        """Run the full pipeline and return the response dict (Arabic-only).

        Never raises for an unresolved root: returns `root: None` with a helpful
        `message` (the router returns 200)."""
        resolved = self.lisan.resolve_root(word)
        root = resolved["root"]
        synthesis_source = self._synthesis_source()

        if root is None:
            return {
                "word": word,
                "root": None,
                "root_source": None,
                "maqayis": None,
                "occurrences": [],
                "occurrences_count": 0,
                "verse_ids": [],
                "madar_synthesis": None,
                "synthesis_source": synthesis_source,
                "synthesis_disclaimer": SYNTHESIS_DISCLAIMER,
                "convergence_note": None,
                "message": (
                    f"تعذّر إيجاد جذر عربي للكلمة «{word}». "
                    "قد تكون اسمَ علمٍ أو كلمةً خارج المعجم القرآني."
                ),
            }

        occ = self._occurrences(root)
        entry = self.store.lookup(normalize_root(root))
        # Readable joined form (no sentinel) for the optional synthesis/convergence.
        asl_text = (
            " ".join(entry.asl_list())
            if (entry and entry.asl_status == "has_asl")
            else None
        )
        maqayis = entry.to_dict() if entry else None

        synthesis, synth_note = self._synthesize(root, asl_text, occ)
        convergence = self._convergence(root, asl_text)

        return {
            "word": word,
            "root": root,
            "root_source": resolved["root_source"],
            "maqayis": maqayis,
            "occurrences": occ["sample"],
            "occurrences_count": occ["count"],
            "verse_ids": occ["verse_ids"],
            "madar_synthesis": synthesis,
            "synthesis_source": synthesis_source,
            "synthesis_disclaimer": SYNTHESIS_DISCLAIMER,
            "convergence_note": convergence,
            "message": synth_note,
        }

    def _synthesis_source(self) -> str:
        """Auditable origin tag for the synthesis field, e.g. 'qwen2.5:7b-local'."""
        model = getattr(self.llm, "model", None) or "qwen2.5:7b"
        provider = getattr(self.llm, "provider", "ollama")
        return f"{model}-local" if provider == "ollama" else model


def _shared_content_words(a: str, b: str) -> set[str]:
    """Content words (≥3 chars, non-stopword) common to two Arabic strings,
    compared on their hamza-safe normalized form."""
    return _content_words(a) & _content_words(b)


_CONV_STOP = {"على", "عن", "الى", "من", "في", "او", "ثم", "وهو", "شيء", "الشيء", "يدل", "تدل"}


def _content_words(text: str) -> set[str]:
    out: set[str] = set()
    for tok in re.split(r"[\s،.:؛«»()\"؛]+", text):
        w = normalize_search(tok)
        if w.startswith("ال") and len(w) > 4:   # drop the definite article
            w = w[2:]
        if len(w) >= 3 and w not in _CONV_STOP:
            out.add(w)
    return out


if __name__ == "__main__":
    from retrieval.lexical_retriever import LexicalRetriever

    svc = MadarService(LexicalRetriever(), llm=None)
    for w in ["رحمة", "لحد", "زقزقة"]:
        out = svc.analyze(w)
        print(f"\n=== {w} → root={out['root']} ({out['root_source']}) ===")
        m = out["maqayis"]
        print("  aṣl:", (m["asl_text"] if m else None), "| status:",
              m["asl_status"] if m else None)
        print("  occurrences:", out["occurrences_count"],
              "| sample:", len(out["occurrences"]))
        if out["occurrences"]:
            o = out["occurrences"][0]
            print(f"    e.g. {o['surface']} [{o['surah']}:{o['ayah']}]")
        print("  synthesis:", out["madar_synthesis"], "| note:", out["message"])
        print("  convergence:", out["convergence_note"])
