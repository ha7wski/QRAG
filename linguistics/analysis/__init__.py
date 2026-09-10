"""
analysis — QLisan's data layer and the word-level analyses built on it.

    qlisan_data.py   the four treebank indexes, served from the registry's caches
    word_analysis.py the per-word fiche (صرفي / نحوي / دلالي)
    mizan.py         الميزان الصرفي — the pattern a word is projected onto
    qac_labels.py    QAC tag → Arabic grammatical label
    fassila.py       الفواصل — the rhyme-ending analysis, per sūra and overall

The only one of the four engines that had no `__init__.py`: it worked as an
implicit namespace package, and the inconsistency was invisible until the move.
"""
