## 1. Arbitration decisions (human verdicts, no code)

- [x] 1.1 Record the settled doctrine in the arbitration file header: proper nouns keep a flagged
      root; a silence never beats a claim; lexicon outranks corpus frequency; contested roots stay
      ranked; two lexica disagreeing means keep both (Maqāyīs primary), with no multi-lexicon
      machinery built while only Maqāyīs is on disk
- [x] 1.2 Freeze the fused-compound lemma list (`ايها` 153, `ايتها` 2, `يوميذ` 70 = 225 words) by
      applying the usage test — "shown bare, does this root mislead about the word's origin?" — and
      eyeball the rooted vocative compounds it must exclude (يَٰقَوْمِ 15, يَٰٓأَهْلَ 12, يَٰبَنِيَّ 10,
      يَٰٓأُو۟لِى 5). Enumerate; write no structural predicate — same shape, opposite verdicts
- [x] 1.3 Arbitrate ٱلنَّاس (241 words, `أنس` vs `نوس`): confirm primary/alternate and cite the lexical entries
- [x] 1.4 Arbitrate the proper-noun block (74 words: `أدم`, `مسح`, `مدن`, `هود`, `حمد`, `حيي`, `سبأ`, …)
- [x] 1.5 Accept the 73 treebank-only additions under rule 2, and cite Maqāyīs only for the weak
      ones (`اني` on the interrogative أَنَّىٰ, 28 words) rather than for all 73
- [x] 1.6 Arbitrate the spelling variants (66 words: `ندي`/`ندو` 53, `طمأن`/`طمن` 13)
- [x] 1.7 Arbitrate the 7 known bugs (`لؤلؤ`/`لالا` ×6, ٱلْمَاعُون ×1) and the remaining tail families
- [x] 1.8 Fill the `verdict` column of `eval/roots/ambiguities.tsv` for all 763 rows, one authority per line

## 2. Arbitration file

- [x] 2.1 Define the `data/references/root_arbitration.json` schema: family-keyed entries with
      chosen primary, alternates, deciding rule, authority; per-word override entries
- [x] 2.2 Generate the file from the arbitrated TSV
- [x] 2.3 Add a validator: reject an entry with no authority, an unknown ref/family, or an
      alternate equal to the primary under either fold

## 3. Resolver

- [x] 3.1 Add the root resolver module: loads both resources plus the arbitration file, applies the
      ordered cascade (0 verdict → 1 fold-equal → 2 single claim → 3 lexicon → 4 attestation → 5 keep both)
- [x] 3.2 Emit the resolved artifact: word ref → primary, alternates, deciding rule, authority
- [x] 3.3 Expose the query path: fold an arbitrary user root and map it to the canonical root
- [x] 3.4 Emit the fused-compound marker as a lemma-list lookup against the list frozen in 1.2
      (never a computed predicate), plus the weak-addition flag from 1.5, as fields on the
      resolved artifact; assert no marker lands on a rootless word
- [x] 3.5 Assert the invariant at build time: 0 words whose resolved root set differs between the
      two chains; 139 hamzated roots present in the output
- [x] 3.6 Verify the resolver is a pure spelling-restoration no-op when the arbitration file is empty

## 4. Chain A — morphology

- [x] 4.1 Move `ingestion/qac_morphology.py` onto the resolver; store exact spellings, keys become exact
- [x] 4.2 Carry alternates into `qac_resolution.json` so form→root resolution reaches both readings
- [x] 4.3 Update `retrieval/lexical_retriever.py` and `retrieval/verse_lookup.py` to query via the resolver
- [x] 4.4 Update `retrieval/root_channel.py` and `retrieval/similar_verses.py`: match on any root,
      dedup per word, count only under the primary so IDF weights stay undistorted
- [x] 4.5 Rebuild and confirm ٱلنَّاس is reachable under both `أنس` and `نوس`, each word listed once

## 5. Chain B — treebank index

- [x] 5.1 Move `ingestion/qac_treebank.py` onto the resolver; stop writing the treebank's raw root column
- [x] 5.2 Store `root` as the exact spelling, expose alternates, index words in `root_graph.json`
      under primary and alternates
- [x] 5.3 Update `analysis/{qlisan_data,word_analysis,qac_labels,fassila}.py` and
      `api/routers/tahlil.py` to read the arbitrated root set
- [x] 5.4 Confirm `analysis/mizan.py` walks `لؤلؤ` radicals, not `لالا`
- [x] 5.5 Extend naẓāʾir scoping to cover the alternate root, grouped by lemma, each occurrence once
- [x] 5.6 Render the contested-root note in QLisan («الجذر الأساسي: أنس، ويُقرأ أيضًا: نوس»),
      outside the «معطى محقّق» badge, absent when the root is uncontested
- [x] 5.7 Render the fused-compound notice on the صرفي level, consistent with the البنية الصرفية
      segment row and outside the badge

## 6. Regression gate

- [x] 6.1 Turn the eval comparison into a repeatable check reporting agree / disagree / per-type counts
- [x] 6.2 Fail the check on any disagreement neither auto-resolved (rules 1, 2, 4) nor covered by
      an arbitration entry, naming the word, both candidates, and the family size
- [x] 6.3 Wire the check into `ingestion/run_pipeline.py` once the unarbitrated count reaches 0

## 7. Verification

- [x] 7.1 Full pipeline rebuild from raw, then rebuild the indexes
- [x] 7.2 Re-run `tests/eval/evaluate.py` and `tests/eval/search_eval.py`; compare against the
      pre-change baseline and account for any delta
- [x] 7.3 Re-measure the mīzān اجتهادي rate so this change is not confounded with `harden-mizan-irregular-roots`
- [x] 7.4 Spot-check the fiche for ٱلنَّاس, لُؤْلُؤ, ٱلْمَاعُون, ءَادَم, يَٰٓأَيُّهَا end to end in the UI
- [x] 7.5 Update `CLAUDE.md`: root spelling is now exact, the resolver is the sole access path,
      and the folded form is a key only
