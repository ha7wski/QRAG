"""
lisan/ — Letter-level ("Lisan") interpretation of an Arabic root.

Reads the interpretive Arabic meaning of each root letter, in sequence, from the
sound-symbolism dataset (Hasan Abbas' framework + classical makhraj/sifat +
an Ibn Jinni sound-imitation note), and composes them DETERMINISTICALLY (no LLM,
see `synthesis_template`) into one coherent reading of the root.

Arabic-only: the module reads solely the `_ar` dataset fields and never branches
on language. This is an INTERPRETIVE heuristic, not lexicography — the disclaimer
is carried in every response. Pure pipeline logic lives here; the FastAPI layer
is in `api/routers/lisan.py`.
"""
