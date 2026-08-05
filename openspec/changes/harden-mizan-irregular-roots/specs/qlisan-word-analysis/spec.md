## ADDED Requirements

### Requirement: Mīzān derivation is layered, class-aware, and pattern-first

The صرفي mīzān for a word SHALL be derived deterministically (no LLM, no network) by
applying, **in this fixed order**, three layers before the legacy raw letter-projection:
(1) classify the QAC root; (2) attempt a curated-pattern match using an
إعلال/إبدال-tolerant radical matcher, and if a pattern matches, **emit that pattern's
canonical mīzān**; (3) only if no pattern matches, fall back to the raw letter-by-letter
projection of the root onto ف-ع-ل. The root and its vocalization SHALL remain verbatim
from QAC/chakl; the mīzān SHALL be computed on the fly with no stored/precomputed result.

#### Scenario: Broken-plural word yields its canonical pattern mīzān

- **WHEN** the mīzān is computed for آلاء (root ألو, a جمع تكسير whose third radical و
  surfaced as hamza)
- **THEN** the pattern layer matches أَفْعَال and the emitted mīzān is «أَفْعَال»
- **AND** the result is `verified=True`
- **AND** the mīzān is never «فَعَاء» (the stranded raw projection).

#### Scenario: Layer order — pattern match wins over raw projection

- **WHEN** a word matches a curated pattern AND would also produce some raw projection
- **THEN** the pattern layer resolves first and its canonical mīzān is returned
- **AND** the raw projection is used only when no curated pattern matches.

### Requirement: Root morphological class is computed and exposed

`compute_mizan` SHALL classify the QAC root from its letters alone into exactly one
**weak-letter class** — صحيح سالم / مضاعف / مثال / أجوف / ناقص / لفيف (plus رباعي for four-letter
roots) — and SHALL expose that class in its result so it can drive class-gated إعلال rules, the
traceability tag, and the tests. A حرف علة SHALL be و or ي only; hamza SHALL NOT count as a weak
letter for classification. Because a root may be both hamzated and weak, the hamzated radical
position(s) SHALL be exposed as a **separate, orthogonal attribute** rather than as a rival
class label, and SHALL NOT gate the إعلال rules. The class precedence SHALL be pinned and
documented (لفيف → مضاعف → أجوف → ناقص → مثال → صحيح سالم).

#### Scenario: Each class is identified from the root letters

- **WHEN** the class is computed for قول (أجوف: middle radical و), دعو (ناقص: last radical و),
  مدد (مضاعف: last two radicals identical), وعد (مثال: first radical و), وقي (لفيف: first and
  last radicals both weak), and رحم (صحيح سالم)
- **THEN** each root is assigned its correct class
- **AND** the assigned class is present in the `compute_mizan` result.

#### Scenario: A hamzated weak root keeps its weak class plus a hamza attribute

- **WHEN** the class is computed for the root of آلاء (QAC root `الو`, whose فاء is a hamza
  folded onto alif and whose لام is و)
- **THEN** the class is **ناقص** (not لفيف — hamza is not a حرف علة)
- **AND** the hamzated position of the فاء is reported through the separate hamza attribute
- **AND** for سأل (QAC root `سال`), whose only irregular radical is a hamza, the class is
  صحيح سالم with the hamza attribute marking the عين.

### Requirement: إعلال/إبدال-tolerant matching keeps verified with a recorded rule

The radical↔surface matcher SHALL, **conditioned on the root class**, resolve a
weak/hamzated radical against a mutated or absent surface letter: إعلال بالقلب (a و/ي
radical MAY match a surface ا, ى, or ء), إعلال بالحذف (a weak radical MAY be absent on the
surface and be consumed with no output letter), and known إبدال (assimilated تاء الافتعال,
hamzat waṣl). When a radical is resolved through such a rule the result SHALL stay
`verified=True` and SHALL record which rule was applied. An إعلال rule SHALL NOT be applied
to a root class for which it is invalid.

#### Scenario: إعلال بالقلب resolves a mutated radical, verified with a trace

- **WHEN** the mīzān is computed for قَالَ (root قول, أجوف) where the middle و surfaced as ا
- **THEN** the mīzān is «فَعَل» — the base pattern, with the module's pre-existing rule
  stripping the final iʿrāب mark exactly as it does for «يَفْعَل» and «فَعَال»
- **AND** the عين slot carries a fatḥah even though the surface alif bears no ḥarakah,
  because an alif *is* a lengthened fatḥah and cannot hold one (without this the mīzān
  would read «فَعل», with a vowelless عين)
- **AND** the result is `verified=True` and records the applied إعلال بالقلب rule.

#### Scenario: إعلال بالحذف consumes a deleted weak radical empty

- **WHEN** the mīzān is computed for the jussive/imperative يَدْعُ (root دعو, ناقص) whose لام
  (the weak radical و) is deleted on the surface
- **THEN** the deleted weak radical is consumed with no output letter (not left stranded)
- **AND** the result stays `verified=True` with the deletion rule recorded.

#### Scenario: إعلال بالحذف on the فاء of a مثال verb

- **WHEN** the mīzān is computed for يَعِدُ (35:40:28, root وعد, مثال) whose initial و (the فاء)
  is deleted in the مضارع
- **THEN** the deleted فاء is consumed with no output letter, rather than leaving the ف slot
  stranded as today's «يَعِد»
- **AND** the result is `verified=True` with the deletion rule recorded.

#### Scenario: A لفيف مفروق word resolves both weak radicals

- **WHEN** the mīzān is computed for يُوحَ (6:93:13, root وحي, لفيف مفروق) where the فاء و
  surfaces and the لام ي is deleted
- **THEN** both weak radicals are resolved — one matched, one consumed empty — instead of
  today's stranded «يُفع»
- **AND** the result is `verified=True` with the applied rule(s) recorded.

#### Scenario: إبدال of تاء الافتعال needs no radical rule

- **WHEN** the mīzān is computed for اصْطَفَىٰ (2:132:9, root صفو) or اسْتَوْقَدَ (2:17:4,
  root وقد), where the تاء of افتعل became ط after an emphatic, or a hamzat waṣl opens
  the form
- **THEN** those letters are recognised as **pattern** letters, copied verbatim, and every
  radical still matches directly — «افْطَعَل» and «اسْتَفْعَل», both `verified=True`
- **AND** no dedicated إبدال rule is required for them.

#### Scenario: An assimilated فاء is left uncovered rather than guessed

- **WHEN** the mīzān is computed for مُتَّقِين (2:2:7, root وقي), whose weak فاء is
  assimilated *into* the تاء الافتعال so that one surface letter (تّ) stands for two mīzān
  letters (فْت)
- **THEN** the result is `verified=False` and the word is logged, because the copy-based
  projection cannot express a one-letter-to-two expansion
- **AND** it is NOT resolved by deleting the فاء instead, which produced a complete-looking
  but wrong «مُتَّعِلن» under the verified badge.

#### Scenario: A class-invalid إعلال rule is never applied to a regular root

- **WHEN** the mīzān is computed for a صحيح سالم root (e.g. رحم)
- **THEN** no إعلال-قلب/حذف substitution is attempted
- **AND** the regular projection/pattern result is unchanged from today.

### Requirement: A geminated (مضاعف) root resolves to verified via shadda fusion

A word whose root has identical second and third radicals SHALL be resolved by a shadda-fusion
rule that consumes both radicals against the single geminated surface letter, and SHALL be
flagged `verified=True`. The blanket "geminated root ⇒ `verified=False`" special-case SHALL be
removed: a geminate's mīzān is deterministic (مَدَّ is فَعَلَ in origin, أصله مَدَدَ, and فَعَّ
after إدغام), not a conjecture, so it SHALL NOT be tagged اجتهادي. The emitted `wazn` SHALL be
the fused, surface-faithful form (فَعَّ), consistent with the module's rule that the mīzān
mirrors the surface vocalization; the pre-إدغام أصل (فَعَلَ) SHALL be carried in the rule trace.

#### Scenario: A geminate verb is verified, not اجتهادي

- **WHEN** the mīzān is computed for مَدَّ (13:3:3, root مدد)
- **THEN** the emitted mīzān is the fused form «فَعّ» (the trailing iʿrāب mark stripped as
  everywhere else, leaving the shadda)
- **AND** the result is `verified=True` with the إدغام fusion rule recorded
- **AND** the pre-إدغام أصل «فَعَلَ» is available in the trace
- **AND** the word is never tagged اجتهادي.

#### Scenario: A geminate stem composes with its suffix

- **WHEN** the mīzān is computed for رَبِّهِمْ (2:5:5) and رَبَّكُمُ (2:21:4), root ربب
- **THEN** the results are «فَعِّهِمْ» and «فَعَّكُمُ» — the fused stem followed by the suffix
  copied verbatim
- **AND** both are `verified=True`.

### Requirement: verified / اجتهادي semantics for the mīzān

The mīzān SHALL be flagged `verified=True` (rendered under the «معطى محقّق» badge) when a
curated pattern matched OR the projection succeeded with every radical resolved (possibly
via a recorded إعلال/إبدال rule). It SHALL be flagged `verified=False` (rendered as the
اجتهادي heuristic hint, outside the badge) **only** when no pattern matched AND the
projection left one or more radicals unresolved. Every `verified=False` word SHALL be
logged so remaining coverage can be measured.

#### Scenario: Resolved-via-rule mīzān is verified, not heuristic

- **WHEN** a word's mīzān is produced through a curated pattern or a recorded إعلال rule
- **THEN** the result is `verified=True`
- **AND** it is not tagged اجتهادي.

#### Scenario: An alignment that needed two إعلال rules is not trusted

- **WHEN** closing the projection for a word required **two different** إعلال rules
  (e.g. تَقِيًّا, 19:13:6, root وقي, needing both قلب and حذف, which yields the malformed
  «تَعِيًّل» with a letter after the word-final tanwīn)
- **THEN** the result is `verified=False` even though every radical was accounted for
- **AND** the word is logged, because an alignment that bends the word twice to make the
  radicals fit is not evidence that the mīzān is right.

#### Scenario: Genuinely uncovered word is اجتهادي and logged

- **WHEN** no curated pattern matches a word AND its raw projection leaves radicals unresolved
- **THEN** the result is `verified=False` (tagged اجتهادي)
- **AND** the word is written to the coverage log.

### Requirement: The awzān / broken-plural table is a versioned, documented data source

The curated pattern library (derived-singular awzān and جموع التكسير) SHALL live in a
versioned data file, each entry a template with ف/ع/ل slots plus fixed letters/vowels that
emits a canonical mīzān, and the file SHALL carry an in-file provenance note citing the
صرف source for the schemes. Patterns and roots SHALL be prioritized to those actually
present in the Qurʾānic corpus; the mīzān SHALL NOT be read from a precomputed per-word
store.

#### Scenario: Pattern table is data, not inlined constants

- **WHEN** the pattern library is consulted during mīzān derivation
- **THEN** its patterns are loaded from the versioned data file (not hard-coded ad hoc)
- **AND** the file documents the source of the schemes it lists.

### Requirement: Pattern family selection is gated on the QAC number feature

Each pattern entry SHALL be tagged with the family it belongs to (derived singular vs جمع
تكسير), and matching SHALL consult the word record's `features.number` to order candidates: a
word tagged `number == "P"` SHALL try the broken-plural templates first, any other word the
singular templates first. The gate SHALL **order** candidates, not hard-filter them, so a record
with missing or unexpected `number` degrades to the un-gated behaviour rather than failing. The
gate SHALL NOT test for `"S"`: singular nouns in the corpus carry no `number` feature at all.

#### Scenario: An ambiguous فِعَال surface is disambiguated by number

- **WHEN** the mīzān is computed for كِتَابٌ (2:89:3, root كتب, carrying **no** `number`
  feature) and for رِجَالٌ (7:46:5, root رجل, `number="P"`) — identical فِعَال surfaces, one a
  derived singular and one a جمع تكسير
- **THEN** the singular is matched against the singular family and the plural against the
  broken-plural family
- **AND** both still yield «فِعَال» with `verified=True`
- **AND** a plural-only scheme (e.g. مَفَاعِل for مَسَاجِدَ at 2:114:5, `number="P"`) is not
  offered first to a word carrying no `number`.

### Requirement: Every curated pattern is covered by a gold assertion

Because a matched pattern places its mīzān **under** the «معطى محقّق» badge, a mis-entered
pattern would render a wrong mīzān with no visible warning — a worse outcome than an honest
اجتهادي. Therefore every pattern present in the data file SHALL be covered by at least one
gold-set assertion pinning a real corpus word to that pattern's output, and a pattern with no
such assertion SHALL NOT ship. After a pattern is added, a sample of the words that newly flip
to `verified=True` **because of that pattern** SHALL be inspected — a drop in the aggregate
اجتهادي rate SHALL NOT be accepted as evidence that a pattern is correct, since a wrong pattern
lowers that rate too. Where a scheme is doubtful it SHALL be omitted, leaving affected words
honestly اجتهادي and enumerable in the coverage log.

#### Scenario: An uncovered pattern does not ship

- **WHEN** the pattern data file is reviewed before release
- **THEN** every entry has at least one gold assertion binding it to a real corpus word
- **AND** any entry without one is removed rather than shipped untested.

#### Scenario: Newly verified words are inspected per pattern

- **WHEN** a pattern is added and the coverage measurement is re-run
- **THEN** a sample of the words that newly became `verified=True` under **that** pattern is
  inspected for correctness
- **AND** the aggregate اجتهادي drop alone is not treated as proof of correctness.

### Requirement: Regular mīzān results do not regress and coverage improves measurably

The layered derivation SHALL NOT change the mīzān of words that are already produced
correctly by the regular path, and the overall اجتهادي rate on a Qurʾānic sample SHALL be
measured before and after and SHALL fall markedly. A curated gold set SHALL pin the
expected mīzān and `verified` flag for representative regular, irregular, and broken-plural
words.

#### Scenario: Known-good regular words stay correct

- **WHEN** the mīzān is computed for رَحِيم (رحم), كِتَاب (كتب), رُسُل (رسل), and مَسَاجِد (سجد)
- **THEN** the results are «فَعِيل», «فِعَال», «فُعُل», and «مَفَاعِل» respectively
- **AND** each is `verified=True`.

#### Scenario: اجتهادي rate drops on a corpus sample

- **WHEN** the اجتهادي rate is measured on the same Qurʾān sample before and after the change
- **THEN** the after-rate is markedly lower than the before-rate
- **AND** the remaining اجتهادي words are enumerated from the coverage log.

#### Scenario: Every root class is covered by a gold case

- **WHEN** the gold set is reviewed against the root-class list
- **THEN** each class — صحيح سالم, مضاعف, مثال, أجوف, ناقص, لفيف, رباعي — has at least one
  pinned case, including the previously-uncovered مثال (يَعِدُ 35:40:28) and لفيف
  (يُوحَ 6:93:13)
- **AND** the per-class acceptance check in the final measurement is therefore backed by a test
  for every class it reports on.
