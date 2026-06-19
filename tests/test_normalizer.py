"""Unit tests for the Arabic text normalizer (ingestion/normalizer.py).

Pure-function tests — no Qdrant, Ollama, or network. Assertions target
behavior guaranteed by the code regardless of whether pyarabic is installed.
"""
from ingestion.normalizer import normalize_text

# Standard harakat that must never survive normalization. (Note: the dagger
# alif U+0670 "ٰ" is intentionally NOT stripped — it is preserved, see the
# bismillah test below.)
STANDARD_HARAKAT = "ًٌٍَُِّْ"


def test_empty_and_none_return_empty_string():
    assert normalize_text("") == ""
    assert normalize_text(None) == ""  # falsy guard, not a crash


def test_strips_standard_harakat():
    out = normalize_text("الرَّحِيم")
    assert not any(ch in out for ch in STANDARD_HARAKAT)
    assert out == "الرحيم"


def test_bismillah_skeleton_keeps_dagger_alif():
    # Documents the real behavior: standard diacritics are stripped, alif wasla
    # ٱ -> ا, but the dagger alif ٰ (U+0670) in الرحمٰن is preserved.
    out = normalize_text("بِسْمِ ٱللَّهِ ٱلرَّحْمَٰنِ ٱلرَّحِيمِ")
    assert out == "بسم الله الرحمٰن الرحيم"


def test_alif_wasla_becomes_plain_alif():
    assert normalize_text("ٱلله") == "الله"


def test_hamza_carrying_letters_are_removed():
    # pyarabic's normalize_hamza maps أ إ آ ؤ ئ to a bare hamza, which the
    # standalone-hamza rule then removes; ى is normalized to ي.
    assert normalize_text("علىؤئء") == "علي"


def test_normalizes_alif_maqsura_to_ya():
    assert normalize_text("هدى") == "هدي"


def test_strips_tatweel():
    assert normalize_text("رحـــمة") == "رحمة"


def test_collapses_whitespace():
    assert normalize_text("  الله   الرحمن  ") == "الله الرحمن"


def test_is_idempotent():
    src = "إِنَّآ أَعْطَيْنَٰكَ ٱلْكَوْثَرَ"
    once = normalize_text(src)
    assert normalize_text(once) == once
