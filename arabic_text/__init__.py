"""
arabic_text — the Arabic text and root primitives, in one place so the choice
between them is visible at the moment it is made.

This project's most repeated footgun is picking the wrong normalizer. It is
silent: the wrong one still returns Arabic, still looks right in a review, and
fails only as a word that mysteriously never matches, or a root family that
quietly merged with another. It has caused real bugs more than once. The three
functions lived in three different packages, so nothing ever put them side by
side.

    ┌──────────────────┬─────────────────────┬──────────────────────┬──────────────────┐
    │ function         │ hamza               │ use for              │ NEVER for        │
    ├──────────────────┼─────────────────────┼──────────────────────┼──────────────────┤
    │ normalize_text   │ DELETES it          │ the pipeline's       │ matching, roots  │
    │                  │ (أشده → شده)        │ `text_ar_clean`      │                  │
    │ normalize_search │ folds carriers,     │ BM25 index + query,  │ roots            │
    │                  │ KEEPS hamza         │ display matching     │                  │
    │ normalize_root   │ folds carriers,     │ root keys and root   │ free text        │
    │                  │ never deletes       │ comparison           │ (leaves ة, ى)    │
    └──────────────────┴─────────────────────┴──────────────────────┴──────────────────┘

`normalize_search` is `normalize_root` plus waqf-mark stripping and ى → ي, ة → ه.
That layering is deliberate: the index and the query must fold identically, and
building the search fold ON the root fold is what guarantees the hamza rule can
never diverge between them.

Alongside them, the two hamza FOLDS that decide whether two spellings denote one
root — `fold_blind` and `fold_carrier`. Neither alone answers the question:
`رأي`/`رئى` agree only when hamza-blind, `لؤلؤ`/`لولو` only under the carrier fold.

**The stored root is the EXACT spelling; a fold is a lookup key, never a stored
value.** `لؤلؤ` is stored as `لؤلؤ`, and a query typed `لولو` or `لالا` still
finds it, because folding happens on the way in.

Mark ranges live in `marks.py`, defined once and written with `\\u` escapes only —
never a literal Arabic character class, which is unreviewable under bidirectional
reordering and can silently swallow letters.

**This package imports nothing from the project.** It is the bottom of the
dependency order; every other layer may use it.
"""
from __future__ import annotations

from arabic_text.folds import fold_blind, fold_carrier
from arabic_text.marks import (
    HARAKAT,
    QURANIC_MARKS,
    TATWEEL,
    bare,
    strip_harakat,
)
from arabic_text.normalize import normalize_root, normalize_search, normalize_text

__all__ = [
    "HARAKAT",
    "QURANIC_MARKS",
    "TATWEEL",
    "bare",
    "fold_blind",
    "fold_carrier",
    "normalize_root",
    "normalize_search",
    "normalize_text",
    "strip_harakat",
]
