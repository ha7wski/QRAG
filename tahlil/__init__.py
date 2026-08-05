"""
tahlil/ — the Tahlil (تحليل) integral word analysis: the five-block page that COMPOSES
the deterministic QLisan levels and adds the generated تعليل + تركيب on top.

Founding constraint: **تفسير القرآن بالقرآن**. Meaning is anchored on exactly three
internal/linguistic pillars — the letters of the root (phono-semantics), the Quran's own
usage (النظائر as empirical proof), and purely linguistic core-sense lexicons (Maqāyīs).
No tafsīr, no أسباب النزول, no external commentary enters any path in this package.

Module map:
  huruf.py       block 1 — the Hasan Abbas letters table (fact صفات vs interpretive دلالة)
  form_kb.py     the versioned دلالة الصيغة KB + the باب contrast table
  evidence.py    the evidence bundle — the ONLY thing the generator ever sees
  citations.py   the cite-or-omit gate (drops/downgrades before rendering)
  coverage.py    the coverage log (drops AND downgrades, triageable per source)

**The badge invariant that everything here serves:** محقّق may only be produced by a code
path that reads the treebank or derives from it deterministically; the generation path is
structurally incapable of emitting it (`citations.py` drops such a claim rather than
re-badging it). مُولَّد means *we checked where this came from*, never *we checked that it
is right*.
"""
