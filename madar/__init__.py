"""
madar/ — Sourced lexical reading of an Arabic root (the *madār*, the pivot).

Epistemic sibling of `lisan/`, and its inverse: where `lisan/` gives an
INTERPRETIVE letter-symbolism reading, `madar/` gives a SOURCED lexical one —
Ibn Fāris' canonical *aṣl* (cited, verified) + the root's Quranic occurrences
(empirical proof) + an optional, clearly-flagged LLM synthesis of the pivot.

Strict separation of epistemic status is the whole point: the cited aṣl and the
generated synthesis never bleed into each other, in the data or the UI. This
package does not modify `lisan/`; it reuses the shared QAC resolver.
"""
