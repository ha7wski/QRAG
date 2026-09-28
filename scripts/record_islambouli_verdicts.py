#!/usr/bin/env python3
"""
record_islambouli_verdicts.py — the Islambouli measurement's recording path.

Subcommands, in the order the protocol runs them:

    bundle OUT_DIR   build the blind uses-writer's prompts (design.md §D13): the
                     procedure, then per root its occurrence verses and Ibn Fāris'
                     aṣl verbatim — and nothing from the letter table. One prompt
                     per batch, same template, packed by verse volume, because
                     the 41 roots' verses do not fit one prompt.

The bundle is built from `morphology.json`, the vocalized corpus and
`maqayis_asl.csv`, and from nothing else. It never reads a file of the Islambouli
engine, which the test for this script checks by reading its source.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from arabic_text import normalize_root  # noqa: E402
from quran_data import corpus, loaders  # noqa: E402
from linguistics.lisan.harness.draw import DEVELOPMENT_CASE  # noqa: E402

# Verse characters per prompt. أمن alone carries ~128 000, so a batch holds at
# least one root of any size.
BATCH_CHARS = 140_000

PROMPT_TEMPLATE = """\
You are writing reference data for a measurement. Do NOT use any tool — no file
reading, no search, no command. Everything you may use is in this message.

TASK. For each Arabic root below, write the DISTINCT senses in which the root is
used in the Quran — the senses you can defend from the verses given, not an
exhaustive dictionary entry. Each sense is one entry with:

  gloss  a short Arabic phrase naming the sense as the verses use it
         (for example «<the form>: <what it means in use>»)
  verse  ONE verse reference "surah:ayah" where the root is used in that sense.
         It MUST be one of the references listed under that root.

SOURCES. Use only (1) the root's verses listed below and (2) the aṣl of Ibn
Fāris quoted below for the root. Glosses describe what the word means in the
verse. They say nothing about the root's letters or sounds.

GRANULARITY. List the senses you would defend as distinct. Do not merge senses
you consider distinct, and do not split one sense into several because it occurs
in several contexts.

OUTPUT. Reply with ONE JSON object and nothing else:
{{"roots": {{"<root>": {{"uses": [{{"gloss": "...", "verse": "s:a"}}, ...]}}, ...}}}}
Cover every root below, and only those.

ROOTS ({n} in this batch)
{roots}
"""


def _asl(maqayis: list[dict], root: str) -> dict:
    key = normalize_root(root)
    for row in maqayis:
        if row.get("root_normalized") == key:
            return {
                "preamble": (row.get("asl_preamble") or "").strip(),
                "asl": [a.strip() for a in (row.get("asl_text") or "").split("|||")
                        if a.strip()],
            }
    return {"preamble": "", "asl": []}


def root_block(root: str, morphology: dict, chakl: dict, maqayis: list[dict]) -> tuple[str, int]:
    rec = morphology[root]
    asl = _asl(maqayis, root)
    lines = [f"=== ROOT «{root}» — {rec['count']} occurrences in {len(rec['verses'])} verses",
             "Ibn Fāris' aṣl (verbatim):"]
    if asl["preamble"]:
        lines.append(f"  {asl['preamble']}")
    lines += [f"  - {a}" for a in asl["asl"]] or ["  (none recorded)"]
    lines.append("Verses:")
    size = 0
    for ref in rec["verses"]:
        s, a = map(int, ref.split(":"))
        text = corpus.strip_leading_basmala(s, a, chakl[(s, a)]["text"])
        size += len(text)
        lines.append(f"  {ref} {text}")
    return "\n".join(lines), size


def batches(roots: list[str], sizes: dict[str, int]) -> list[list[str]]:
    """Greedy first-fit by decreasing size — deterministic for a given input."""
    bins: list[tuple[int, list[str]]] = []
    for root in sorted(roots, key=lambda r: (-sizes[r], r)):
        for i, (used, members) in enumerate(bins):
            if used + sizes[root] <= BATCH_CHARS:
                bins[i] = (used + sizes[root], members + [root])
                break
        else:
            bins.append((sizes[root], [root]))
    return [members for _used, members in bins]


def cmd_bundle(args) -> int:
    out = Path(args.out_dir)
    out.mkdir(parents=True, exist_ok=True)
    morphology = loaders.morphology()
    chakl = corpus.chakl_by_ref()
    maqayis = loaders.maqayis_asl()
    roots = [e["root"] for e in loaders.islambouli_witness_set()["roots"]] + [DEVELOPMENT_CASE]
    blocks, sizes = {}, {}
    for root in roots:
        blocks[root], sizes[root] = root_block(root, morphology, chakl, maqayis)
    plan = batches(roots, sizes)
    manifest = []
    for i, members in enumerate(plan, 1):
        prompt = PROMPT_TEMPLATE.format(n=len(members),
                                        roots="\n\n".join(blocks[r] for r in members))
        path = out / f"batch_{i}.txt"
        path.write_text(prompt, encoding="utf-8")
        manifest.append({"batch": i, "roots": members,
                         "verse_chars": sum(sizes[r] for r in members),
                         "prompt_chars": len(prompt)})
    (out / "plan.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=1),
                                   encoding="utf-8")
    for m in manifest:
        print(f"batch {m['batch']}: {len(m['roots'])} roots, {m['prompt_chars']} chars")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    sub = parser.add_subparsers(dest="cmd", required=True)
    b = sub.add_parser("bundle")
    b.add_argument("out_dir")
    b.set_defaults(func=cmd_bundle)
    args = parser.parse_args()
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
