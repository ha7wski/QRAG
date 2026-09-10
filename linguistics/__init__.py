"""
linguistics — the four Arabic study engines.

Ten sibling directories at the repo root gave no clue that `tahlil/` is a feature
engine while `indexing/` is a pipeline stage. The distinction is now visible from
the tree itself:

    PIPELINE   ingestion → indexing → retrieval → generation → api
               the build path and the request path, in the order they read

    DOMAIN     linguistics/{analysis,lisan,madar,tahlil}
               the study engines the product is actually about

    SHARED     arabic_text/  the text and root primitives
               quran_data/   dataset paths, loaders, provenance

Internal module names are unchanged — only this parent was added. Each engine
keeps its own docstring; in particular `linguistics/madar/` is QUARANTINED, and
says so.

Import direction: these packages may use the shared packages and `retrieval/`
(for verse lookup), never `api/`. Nothing imports `linguistics/` except `api/`.
`tests/test_import_direction.py` enforces it.
"""
