"""
lisan/ — Letter-level ("Lisan") interpretation of an Arabic root.

The pipeline runs CORE-FIRST: word → root → the root's attested aṣl(s) from Ibn
Fāris (`root_core_store`) → per-letter sense selection constrained by that core
(`sense_selection`) → deterministic Arabic synthesis (`synthesis_template`).

It used to run the other way — one frozen gloss per letter, chained — and that
is why `خ-ي-ر` read «القذارة والخشونة والخواء … فساد» against «أصله العطف
والميل». A letter carries a BUNDLE of sourced senses (`letter_lexicon`), and
nothing can prefer one over another without knowing what the root means.

No model anywhere in this package, at any layer: the synthesis was an LLM step
until a local model produced fluent prose contradicting the attested sense, and
a model in the *selection* step would rebuild that failure where it is harder to
see. Arabic-only: the modules read solely the `_ar` dataset fields and never
branch on language. This is an INTERPRETIVE framework, not lexicography — the
disclaimer is carried in every response, and a root with no attested aṣl gets a
warning and an unselected inventory instead of a reading.

Pure pipeline logic lives here; the FastAPI layer is in `api/routers/lisan.py`.
"""
