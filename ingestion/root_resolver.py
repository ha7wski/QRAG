"""The single root authority for every Quran word.

Runs BEFORE either processing chain writes, so `qac_morphology.py` (chain A) and
`qac_treebank.py` (chain B) stop deciding roots for themselves and publish the same
answer. Reads the two RAW resources plus the arbitration file; emits one artifact:

    data/processed/roots_resolved.json    "s:a:w" -> {primary, alternates, rule, ...}

Cascade, first rule that answers wins:

    0  a verdict recorded in data/references/root_arbitration.json
    1  the two roots are equal under either fold -> keep the REFERENCE spelling
    2  exactly one resource proposes a root     -> take it
    4  attestation elsewhere in the Quran breaks the tie
       otherwise: unarbitrated (reported, never guessed)

Rules 3 (lexicon) and 5 (two lexica disagree) are human arbitration steps: they are
recorded as entries in the arbitration file and reached here through rule 0. This
module never parses a dictionary at runtime.

Invariant: the fold is a COMPARISON KEY only. The stored root is the exact spelling
carried by the reference source — `لؤلؤ`, never `لولو` (carrier-folded) nor `لالا`
(the treebank's hamza-stripped form).
"""
from __future__ import annotations

import csv
import json
import re
import sys
import unicodedata
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from ingestion.root_normalize import normalize_root  # noqa: E402
from quran_data import loaders, paths, qac  # noqa: E402

TREEBANK_CSV = paths.TREEBANK_CSV
ARBITRATION = paths.ROOT_ARBITRATION_JSON
OUT = paths.ROOTS_RESOLVED_JSON

NULL_TOKENS = {"_", "", "ـ", "-", "(*)"}

# Cross-source fold: hamza-BLIND. The treebank ships every root with its hamza
# stripped (0 hamzated roots out of 1642), so `لؤلؤ` arrives as `لالا`. Folding both
# sides to a bare alif is the only way to see they are the same root. Never stored.
_BLIND = {"ء": "ا", "أ": "ا", "إ": "ا", "آ": "ا", "ٱ": "ا",
          "ؤ": "ا", "ئ": "ا", "ى": "ي", "ة": "ه"}
_BLIND_TABLE = {ord(k): v for k, v in _BLIND.items()}
_MARKS = "".join(chr(c) for c in list(range(0x0610, 0x061B))
                 + list(range(0x064B, 0x0660)) + [0x0670]
                 + list(range(0x06D6, 0x06ED)))
_MARK_TABLE = {ord(c): None for c in _MARKS}
_SEP_RE = re.compile(r"[\s.\-_·+]")


def fold_blind(text: str) -> str:
    """Hamza-blind fold — comparison key only, never a stored value."""
    if not text:
        return ""
    t = unicodedata.normalize("NFC", text).translate(_MARK_TABLE).replace("ـ", "")
    return _SEP_RE.sub("", t).translate(_BLIND_TABLE).strip()


def fold_carrier(text: str) -> str:
    """Project fold (hamza carriers -> carrier letter, bare hamza kept)."""
    return normalize_root(text) if text else ""


def same_root(a: str, b: str) -> bool:
    """Do two spellings denote one root? Equal under EITHER fold.

    Neither fold alone suffices: `رأي`/`رئى` agree only when hamza-blind, while
    `لؤلؤ`/`لولو` agree only under the carrier fold.
    """
    if not a or not b:
        return False
    return fold_carrier(a) == fold_carrier(b) or fold_blind(a) == fold_blind(b)


# ---------------------------------------------------------------- sources
def load_reference() -> dict[str, list[str]]:
    """Chain-A source: word ref -> ROOT: fields, in the file's own spelling.

    The morphology file's four-column layout is known in exactly one place —
    `quran_data.qac` — so this stage and `qac_morphology.py` cannot drift apart
    on how they read it. The result is cached there and shared with any other
    caller in the process.

    **Read-only**: the returned map is shared. Nothing here mutates it.
    """
    return qac.word_roots()


def load_treebank(path: Path = TREEBANK_CSV) -> dict[str, dict]:
    """Chain-B source: word ref -> {root, lemma, proper_noun}.

    Mirrors qac_treebank.py exactly — first STEM segment wins for compound words —
    so a divergence here would be a real one, never a parsing artefact.
    """
    out: dict[str, dict] = {}
    with path.open(encoding="utf-8", newline="") as fh:
        for row in csv.DictReader(fh, delimiter="\t"):
            if row["location"] == "_":
                continue
            key = f'{int(row["chapter_id"])}:{int(row["verse_id"])}:{int(row["word_id"])}'
            rec = out.setdefault(key, {"root": None, "lemma": None,
                                       "proper_noun": False, "_stem": False})
            if row["segment"] != "STEM" or rec["_stem"]:
                continue
            rec["_stem"] = True
            rec["proper_noun"] = row.get("pos", "").strip() == "PN"
            root_ar = (row.get("root_ar") or "").strip()
            if root_ar not in NULL_TOKENS:
                rec["root"] = root_ar
            lemma_ar = (row.get("lemma_ar") or "").strip()
            if lemma_ar not in NULL_TOKENS:
                rec["lemma"] = normalize_root(lemma_ar)
    for rec in out.values():
        rec.pop("_stem", None)
    return out


# ---------------------------------------------------------------- arbitration
class Arbitration:
    """The recorded verdicts. An absent/empty file is legal: the cascade then runs
    on rules 1, 2 and 4 only, and unresolved families are reported, never guessed."""

    def __init__(self, doc: dict | None = None):
        doc = doc or {}
        self.doc = doc
        self.families = {(f["root_A"], f["root_B"]): f for f in doc.get("families", [])}
        self.words = doc.get("words", {})
        self.fused_lemmas = set(
            doc.get("fused_compound_lemmas", {}).get("lemmas", {})
        )

    @classmethod
    def load(cls, path: Path | None = ARBITRATION) -> "Arbitration":
        if path is None or not Path(path).exists():
            return cls({})
        # The registry's file goes through its shared loader; an explicit other
        # path (a fixture, a candidate verdict set) is read as given.
        if Path(path) == ARBITRATION:
            return cls(loaders.root_arbitration())
        return cls(json.loads(Path(path).read_text(encoding="utf-8")))

    def lookup(self, ref: str, key: tuple[str, str]) -> dict | None:
        return self.words.get(ref) or self.families.get(key)

    def authority(self, arb_key: str | None) -> str | None:
        if not arb_key:
            return None
        a, _, b = arb_key.partition("/")
        entry = self.families.get((a, b))
        return entry.get("authority") if entry else None


NO = "-"


class RootResolver:
    """Resolve every word once; both chains read the result."""

    def __init__(self, arbitration: Arbitration | None = None,
                 reference: dict | None = None, treebank: dict | None = None):
        self.arb = arbitration if arbitration is not None else Arbitration.load()
        self.ref = reference if reference is not None else load_reference()
        self.tb = treebank if treebank is not None else load_treebank()
        self._attest = self._build_attestation()
        self._query_index: dict[str, str] | None = None

    # -- rule 4 support ----------------------------------------------------
    def _build_attestation(self):
        """words carrying each root, per source, keyed by the blind fold."""
        a_idx, b_idx = defaultdict(set), defaultdict(set)
        for k, roots in self.ref.items():
            for r in roots:
                a_idx[fold_blind(r)].add(k)
        for k, rec in self.tb.items():
            if rec["root"]:
                b_idx[fold_blind(rec["root"])].add(k)
        return a_idx, b_idx

    def _disagreement_words(self):
        """(root_A, root_B) -> word refs, for 'attested elsewhere' arithmetic."""
        pairs = defaultdict(set)
        for key in self.ref.keys() | self.tb.keys():
            ra = self.ref.get(key, [])
            rb = (self.tb.get(key) or {}).get("root")
            if not ra and not rb:
                continue
            if ra and rb and any(same_root(x, rb) for x in ra):
                continue
            pairs[("|".join(ra) or NO, rb or NO)].add(key)
        return pairs

    # -- the cascade -------------------------------------------------------
    def decide(self, ref: str, pair_words: dict) -> dict | None:
        ra = self.ref.get(ref, [])
        rb = (self.tb.get(ref) or {}).get("root")
        if not ra and not rb:
            return None

        key = ("|".join(ra) or NO, rb or NO)
        # A word whose SOURCE carries several roots (one word in the corpus, 20:94:2
        # يبنؤم = بني + أمم) has one root per segment. Consumers that walk segments
        # must keep each segment's own root there — everywhere else the primary wins,
        # even when it overrides the source.
        multi = {"multi_source": True} if len(ra) > 1 else {}

        # rule 0 — recorded verdict
        entry = self.arb.lookup(ref, key)
        if entry:
            return {"primary": entry["primary"],
                    "alternates": list(entry.get("alternates", [])),
                    "rule": entry.get("rule", 0),
                    "arb": f"{key[0]}/{key[1]}",
                    "weak": bool(entry.get("weak")), **multi}

        # rule 1 — same root, different spelling: the reference spelling wins
        if ra and rb:
            match = [x for x in ra if same_root(x, rb)]
            if match:
                others = [x for x in ra if x not in match]
                return {"primary": match[0], "alternates": others, "rule": 1, **multi}

        # rule 2 — one claim against a silence
        if ra and not rb:
            return {"primary": ra[0], "alternates": ra[1:], "rule": 2, **multi}
        if rb and not ra:
            return {"primary": rb, "alternates": [], "rule": 2}

        # rule 4 — attestation elsewhere breaks the tie
        a_idx, b_idx = self._attest
        kset = pair_words.get(key, set())
        a_else = len(a_idx.get(fold_blind(ra[0]), set()) - kset)
        b_else = len(b_idx.get(fold_blind(rb), set()) - kset)
        if a_else != b_else:
            win, alt = (ra[0], rb) if a_else > b_else else (rb, ra[0])
            return {"primary": win, "alternates": [alt], "rule": 4}

        return {"primary": None, "alternates": [], "rule": None,
                "unarbitrated": True, "candidates": [ra[0], rb]}

    # -- build -------------------------------------------------------------
    def build(self) -> tuple[dict, dict]:
        pair_words = self._disagreement_words()
        resolved: dict[str, dict] = {}
        stats = {"words": 0, "rooted": 0, "rootless": 0, "unarbitrated": [],
                 "by_rule": defaultdict(int), "fused": 0, "multi": 0}

        for ref in self.ref.keys() | self.tb.keys():
            stats["words"] += 1
            out = self.decide(ref, pair_words)
            if out is None:
                stats["rootless"] += 1
                continue
            if out.get("unarbitrated"):
                stats["unarbitrated"].append((ref, out["candidates"]))
                continue

            tb = self.tb.get(ref) or {}
            rec = {"primary": out["primary"], "rule": out["rule"]}
            if out["alternates"]:
                rec["alternates"] = out["alternates"]
                stats["multi"] += 1
            if out.get("arb"):
                rec["arb"] = out["arb"]
            if out.get("weak"):
                rec["weak"] = True
            if out.get("multi_source"):
                rec["multi_source"] = True
            if tb.get("proper_noun"):
                rec["proper_noun"] = True
            # fused-compound marker: a LOOKUP against the frozen lemma list,
            # never a predicate over segments.
            if tb.get("lemma") in self.arb.fused_lemmas:
                rec["fused_compound"] = True
                stats["fused"] += 1
            resolved[ref] = rec
            stats["rooted"] += 1
            stats["by_rule"][out["rule"]] += 1

        stats["by_rule"] = dict(sorted(stats["by_rule"].items()))
        return resolved, stats

    # -- query path (3.3) --------------------------------------------------
    def _build_query_index(self, resolved: dict) -> dict[str, str]:
        idx: dict[str, str] = {}
        for rec in resolved.values():
            for r in [rec["primary"], *rec.get("alternates", [])]:
                for k in (fold_carrier(r), fold_blind(r)):
                    idx.setdefault(k, r)
        return idx

    def resolve_query(self, query: str, resolved: dict | None = None) -> str | None:
        """Map any user spelling of a root onto the canonical stored one."""
        if self._query_index is None:
            self._query_index = self._build_query_index(
                resolved if resolved is not None else self.build()[0])
        q = (query or "").strip()
        return (self._query_index.get(fold_carrier(q))
                or self._query_index.get(fold_blind(q)))


def audit(resolver: "RootResolver", stats: dict) -> dict:
    """Where the two resources stand, as numbers a rebuild can be compared against.

    The disagreement budget is finite and known (757 words / 30 families at the time
    of writing). This reports it per resolving rule so a regression shows up as a
    number rather than as a silently different root.
    """
    pairs = resolver._disagreement_words()
    families = sorted(
        ((f"{a}/{b}", len(ks)) for (a, b), ks in pairs.items()),
        key=lambda kv: -kv[1],
    )
    disagree = sum(n for _, n in families)
    return {
        "words": stats["words"],
        "rooted": stats["rooted"],
        "both_rootless": stats["rootless"],
        "agree": stats["rooted"] - disagree + len(stats["unarbitrated"]),
        "disagree": disagree,
        "families": len(families),
        "by_rule": dict(stats["by_rule"]),
        "unarbitrated": len(stats["unarbitrated"]),
        "top_families": families[:10],
    }


def load_resolved(path: Path = OUT, build_if_missing: bool = True) -> dict:
    """The resolved artifact, for consumers. Builds it if it is not on disk yet.

    The registry's file goes through its shared loader, so the two consumer
    chains in one pipeline process (`qac_morphology`, `qac_treebank`) parse it
    once between them instead of holding a copy each. **Read-only**: neither
    chain mutates what it gets back.
    """
    if Path(path).exists():
        if Path(path) == OUT:
            return loaders.roots_resolved()
        return json.loads(Path(path).read_text(encoding="utf-8"))
    if not build_if_missing:
        raise FileNotFoundError(f"{path} not found — run ingestion/root_resolver.py first")
    resolved, _ = RootResolver().build()
    Path(path).write_text(json.dumps(resolved, ensure_ascii=False), encoding="utf-8")
    return resolved


def run() -> dict:
    """Pipeline stage: resolve every root once, write the artifact, enforce invariants.

    Raises rather than writing when an invariant fails — a disagreement nobody
    arbitrated must stop the build, not reach the corpus as a silent guess.
    """
    r = RootResolver()
    resolved, stats = r.build()
    errors = check(r, resolved, stats)
    if errors:
        report = audit(r, stats)
        raise SystemExit(
            "root resolution failed its invariants — refusing to write "
            f"{OUT.name}:\n  - " + "\n  - ".join(errors)
            + f"\n  disagreements: {report['disagree']} words / {report['families']} families"
            + (f"\n  unarbitrated: {stats['unarbitrated'][:5]}" if stats["unarbitrated"] else "")
            + "\n  Record a verdict in data/references/root_arbitration.json, "
              "or explain why the cascade should settle it."
        )
    OUT.write_text(json.dumps(resolved, ensure_ascii=False), encoding="utf-8")
    report = audit(r, stats)
    print(f"  root-resolve: {stats['rooted']} rooted words, "
          f"{len({rec['primary'] for rec in resolved.values()})} roots "
          f"({stats['multi']} multi-root, {stats['fused']} fused)")
    print(f"               {report['disagree']} source disagreements over "
          f"{report['families']} families, 0 unarbitrated; rules {report['by_rule']}")
    return resolved


def check(resolver: "RootResolver", resolved: dict, stats: dict) -> list[str]:
    """Build-time invariants. Returns a list of violations (empty = sound)."""
    errors: list[str] = []

    # every word carries exactly one root set, and nothing was guessed
    if stats["unarbitrated"]:
        errors.append(f"{len(stats['unarbitrated'])} unarbitrated disagreements "
                      f"(e.g. {stats['unarbitrated'][0]})")

    # both chains will read THIS artifact, so a per-word divergence is impossible by
    # construction; what must be zero is the number of disagreements left unresolved.
    ref_vs_tb = 0
    for ref, rec in resolved.items():
        ra = resolver.ref.get(ref, [])
        rb = (resolver.tb.get(ref) or {}).get("root")
        if ra and rb and not any(same_root(x, rb) for x in ra):
            known = set(rec.get("alternates", [])) | {rec["primary"]}
            if not (known & (set(ra) | {rb})):
                ref_vs_tb += 1
    if ref_vs_tb:
        errors.append(f"{ref_vs_tb} words whose resolved root belongs to neither source")

    # spelling was restored, not folded away
    hamzated = {rec["primary"] for rec in resolved.values()
                if set("ءأإآؤئ") & set(rec["primary"])}
    if len(hamzated) != 139:
        errors.append(f"{len(hamzated)} hamzated roots in the output, expected 139 "
                      "(the reference source carries 139)")
    # rule 1 must return a REFERENCE spelling, never the treebank's stripped one
    bad_spelling = [ref for ref, rec in resolved.items()
                    if rec["rule"] == 1 and rec["primary"] not in resolver.ref.get(ref, [])]
    if bad_spelling:
        errors.append(f"{len(bad_spelling)} rule-1 words not spelled as the reference "
                      f"(e.g. {bad_spelling[0]})")

    # a marker states where a root sits: it cannot land on a rootless word
    stray = [ref for ref, rec in resolved.items()
             if rec.get("fused_compound") and not rec.get("primary")]
    if stray:
        errors.append(f"{len(stray)} fused-compound markers on rootless words")
    marked_lemmas = {(resolver.tb.get(ref) or {}).get("lemma")
                     for ref, rec in resolved.items() if rec.get("fused_compound")}
    if marked_lemmas - resolver.arb.fused_lemmas:
        errors.append(f"markers outside the frozen lemma list: "
                      f"{marked_lemmas - resolver.arb.fused_lemmas}")

    # every deviation from the reference is covered by an arbitration entry
    undocumented = []
    for ref, rec in resolved.items():
        ra = resolver.ref.get(ref, [])
        if ra and rec["primary"] not in ra and not rec.get("arb") and rec["rule"] != 4:
            undocumented.append(ref)
    if undocumented:
        errors.append(f"{len(undocumented)} roots deviate from the reference with no "
                      f"arbitration entry (e.g. {undocumented[0]})")

    return errors


def main() -> None:
    empty = "--empty-arbitration" in sys.argv
    arb = Arbitration({}) if empty else Arbitration.load()
    r = RootResolver(arbitration=arb)
    resolved, stats = r.build()

    hamzated = {rec["primary"] for rec in resolved.values()
                if set("ءأإآؤئ") & set(rec["primary"])}
    print(f"words={stats['words']} rooted={stats['rooted']} rootless={stats['rootless']} "
          f"multi-root={stats['multi']} fused={stats['fused']}")
    print(f"by rule: {stats['by_rule']}")
    print(f"distinct roots={len({rec['primary'] for rec in resolved.values()})} "
          f"hamzated={len(hamzated)}")
    if stats["unarbitrated"]:
        print(f"UNARBITRATED: {len(stats['unarbitrated'])} words")
        for ref, cands in stats["unarbitrated"][:10]:
            print(f"  {ref}: {cands[0]} vs {cands[1]}")

    report = audit(r, stats)
    print(f"\nsource disagreements: {report['disagree']} words over "
          f"{report['families']} families, {report['unarbitrated']} unarbitrated")
    for fam, n in report["top_families"][:6]:
        print(f"    {n:4d}  {fam}")

    errors = check(r, resolved, stats)
    print("\ninvariants: " + ("OK" if not errors else f"{len(errors)} VIOLATION(S)"))
    for e in errors:
        print(f"  - {e}")

    if empty:
        print("\n(--empty-arbitration: artifact NOT written)")
        return
    OUT.write_text(json.dumps(resolved, ensure_ascii=False), encoding="utf-8")
    print(f"wrote {OUT.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
