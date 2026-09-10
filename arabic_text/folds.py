"""
folds.py — the two hamza folds used to decide whether two spellings are one root.

These were exported by the pipeline stage `ingestion/root_resolver.py`, and
imported at runtime by `linguistics/analysis/qlisan_data.py` and
`retrieval/lexical_retriever.py` — a request path reaching into a build step for
a primitive. They are primitives; this is where primitives live. `root_resolver`
keeps its stage duties: the arbitration cascade, its invariants, writing
`roots_resolved.json`, and the lookups over its own output.

Neither fold alone decides the question, which is why both exist:
`رأي`/`رئى` agree only under the hamza-BLIND fold, while `لؤلؤ`/`لولو` agree only
under the CARRIER fold. A third, `fold_madda`, answers a narrower question about
ORTHOGRAPHY rather than about roots — see its docstring.

**A fold is a lookup key, never a stored value.** The stored root is the exact
spelling — `لؤلؤ` is stored as `لؤلؤ` — and a query typed `لولو` or `لالا` finds
it by folding on the way in.
"""
from __future__ import annotations

import re
import unicodedata

from arabic_text.marks import BLIND_FOLD_TABLE, TATWEEL
from arabic_text.normalize import normalize_root

# Hamza-blind: every hamza seat AND the bare hamza collapse onto alif, ى onto ي,
# ة onto ه. This destroys the seat on purpose — it is the coarsest question one
# can ask, "are these the same consonants at all".
_BLIND = {"ء": "ا", "أ": "ا", "إ": "ا", "آ": "ا", "ٱ": "ا",
          "ؤ": "ا", "ئ": "ا", "ى": "ي", "ة": "ه"}
_BLIND_TABLE = {ord(k): v for k, v in _BLIND.items()}

# Separators a root may be written with in one source and not another.
_SEP_RE = re.compile(r"[\s.\-_·+]")

# The Uthmānī spelling of a long ā: a bare hamza followed by an alif, `ءَا`, where
# ordinary orthography writes the madda `آ` and a user usually types a plain `ا`.
# QAC surface forms use it (آيات is stored `ءايات`, قرآنا is `قرءانا`).
_MADDA_DIGRAPH = "ءا"


def fold_blind(text: str) -> str:
    """Hamza-blind fold — comparison key only, never a stored value."""
    if not text:
        return ""
    t = unicodedata.normalize("NFC", text).translate(BLIND_FOLD_TABLE)
    t = t.replace(TATWEEL, "")
    return _SEP_RE.sub("", t).translate(_BLIND_TABLE).strip()


def fold_madda(text: str) -> str:
    """Uthmānī `ءا` → `ا`, so a typed `آيات`/`ايات` meets the stored `ءايات`.

    Comparison key only, applied to SURFACE FORMS on both sides — never to a root
    key, and never a stored value.

    This is NOT hamza deletion, the thing `normalize_text` does and the other two
    normalizers exist to avoid. Only the two-character digraph folds, because only
    the digraph *is* an alif-madda; a lone hamza is a letter and stays one (`جزاء`
    keeps its ء and does not become `جزا`). Without it the bare hamza QAC records
    and the madda a user types could never meet: the lookup missed, and the lenient
    pass went on peeling alifs until it landed on an unrelated but real key —
    `الايات` answered `أتي` (to come) instead of `أيي` (sign).
    """
    return text.replace(_MADDA_DIGRAPH, "ا") if text else ""


def fold_carrier(text: str) -> str:
    """Project fold: hamza carriers to their carrier letter, bare hamza kept.

    This is `normalize_root` — named separately because at a comparison site the
    question being asked is "same root under the carrier fold?", not "what is the
    index key for this?", and the two happen to have the same answer.
    """
    return normalize_root(text) if text else ""
