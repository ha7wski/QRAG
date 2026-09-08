import Link from "next/link";
import FicheRow from "@/components/FicheRow";
import type { QlisanNazair, QlisanSarfi } from "@/lib/types";

/**
 * The rows of a صرفي (morphology) fiche — the `<dl>` body only, with no card
 * shell, so a caller can wrap it in a `LevelCard` (QLisan) or a collapsible
 * `<details>` (the «تحليل نحوي» section of Lisan Analysis).
 *
 * Extracted verbatim from `qlisan/page.tsx::SarfiLevel`; QLisan renders exactly
 * what it rendered before.
 *
 * **Every positional row is conditional, and that is deliberate.** `العلامة`
 * appears only when the caller passes a `marker`, and `الحالة الإعرابية` arrives
 * inside `features`. A word analysed without a verse position (`POST /qlisan/form`)
 * simply arrives with those absent, so the non-positional contract lives in ONE
 * place — the backend — and this component needs no mode flag that could disagree
 * with it. `النظائر` is NOT in that set: root and lemma decide it, so both callers
 * render it.
 */
export default function SarfiRows({
  level,
  marker,
}: {
  level: QlisanSarfi;
  /** العلامة — the derived case-marker hint from the نحوي level. Omit when the
   *  word has no verse position: a case marker is a fact about an occurrence. */
  marker?: string | null;
}) {
  const features = (level.features || []).filter(
    (f) => f && f.label_ar && f.value_ar,
  );

  return (
    <dl className="space-y-3">
      {/* Part of speech (Arabic only — raw QAC code is never rendered). */}
      <FicheRow label="القسم">
        <span className="font-arabic text-lg text-gray-800">
          {level.pos_ar || "—"}
        </span>
      </FicheRow>

      {/* Root (or proper-noun marker). */}
      <FicheRow label={level.is_proper_noun ? "اسم علم" : "الجذر"}>
        {level.is_proper_noun ? (
          <span className="font-arabic text-lg text-gray-800">
            {level.lemma_display || level.root_display || "—"}
          </span>
        ) : (
          <span className="font-arabic text-2xl tracking-widest text-brand-dark">
            {level.root_display || level.root || "—"}
          </span>
        )}
      </FicheRow>

      {/* Contested root — both readings are named rather than one being picked
          silently. Outside the «معطى محقّق» badge: this is an arbitration, not a
          verbatim source field. */}
      {level.root_alternates?.length > 0 && (
        <FicheRow label="قراءة أخرى">
          <span className="flex items-center gap-2">
            <span className="font-arabic text-base text-gray-700">
              {`الجذر الأساسي: ${level.root_display || level.root}، ويُقرأ أيضًا: ${level.root_alternates.join("، ")}`}
            </span>
            <span
              className="rounded bg-amber-50 px-1.5 py-0.5 font-arabic text-xs text-amber-700"
              title="اختلاف بين المصدرين، والترجيح مُوثَّق — خارج نطاق «معطى محقّق»"
            >
              مُرجَّح
            </span>
          </span>
        </FicheRow>
      )}

      {/* Welded word: the root covers one segment, not the whole word — so a reader
          does not infer that يا أيها derives from آية. */}
      {level.fused_compound && (
        <FicheRow label="بنية الكلمة">
          <span className="flex items-center gap-2">
            <span className="font-arabic text-base text-gray-700">
              كلمة مركّبة — الجذر يخصّ أحد مقاطعها لا الكلمة بأكملها
            </span>
            <span
              className="rounded bg-amber-50 px-1.5 py-0.5 font-arabic text-xs text-amber-700"
              title="قراءة لبنية المقاطع — خارج نطاق «معطى محقّق»"
            >
              استنتاجي
            </span>
          </span>
        </FicheRow>
      )}

      {/* Lemma. */}
      {(level.lemma_display || level.lemma) && (
        <FicheRow label="اللفظ">
          <span className="font-arabic text-lg text-gray-800">
            {level.lemma_display || level.lemma}
          </span>
        </FicheRow>
      )}

      {/* Morphological structure — the vocalized TEXT of each segment joined by
          « + » in RTL reading order (prefix on the right); the type (بادئة/جذع/لاحقة)
          is a small secondary label under each segment (also a tooltip). A single
          segment (e.g. يَرْتَع) shows the stem alone, no « + ». */}
      {level.segments && level.segments.length > 0 && (
        <FicheRow label="البنية الصرفية">
          <span className="flex flex-wrap items-start gap-x-1.5 gap-y-1">
            {level.segments.map((seg, i) => (
              <span key={i} className="flex items-start gap-x-1.5">
                {i > 0 && (
                  <span className="self-center font-arabic text-base text-gray-400">
                    +
                  </span>
                )}
                <span className="flex flex-col items-center">
                  <span
                    className="font-arabic text-lg text-gray-800"
                    title={seg.type_ar}
                  >
                    {seg.text}
                  </span>
                  <span className="font-arabic text-[10px] leading-tight text-gray-400">
                    {seg.type_ar}
                  </span>
                </span>
              </span>
            ))}
          </span>
        </FicheRow>
      )}

      {/* الميزان الصرفي — root projected onto ف-ع-ل (just under البنية الصرفية).
          `items-start` = right edge in RTL, so the wazn aligns with the other rows. */}
      {level.mizan && level.mizan.available && level.mizan.wazn && (
        <FicheRow label="الوزن">
          <span className="flex flex-col items-start gap-1">
            <span className="flex items-center gap-2">
              <span className="font-arabic text-xl tracking-widest text-gray-800">
                {level.mizan.wazn}
              </span>
              {!level.mizan.verified && (
                <span
                  className="rounded bg-amber-50 px-1.5 py-0.5 font-arabic text-xs text-amber-700"
                  title="ميزان تقديري (جذر معتلّ/مضعّف) — خارج نطاق «معطى محقّق»"
                >
                  اجتهادي
                </span>
              )}
            </span>
            {level.mizan.bab && (
              <span className="font-arabic text-sm text-gray-500">
                باب {level.mizan.bab}
              </span>
            )}
          </span>
        </FicheRow>
      )}

      {/* العلامة — the derived case marker (from the نحوي level), shown under
          البنية الصرفية as an «الأصل» hint (heuristic, not verbatim corpus data).
          Positional: absent for a word analysed without a verse position. */}
      {marker && (
        <FicheRow label="العلامة">
          <span className="flex items-baseline gap-2">
            <span className="font-arabic text-lg text-gray-800">{marker}</span>
            <span className="font-arabic text-xs text-gray-400">(الأصل)</span>
          </span>
        </FicheRow>
      )}

      {/* Grammatical features — each an ordered Arabic {label_ar, value_ar}. */}
      {features.map((f, i) => (
        <FicheRow key={`${f.label_ar}-${i}`} label={f.label_ar}>
          <span className="font-arabic text-lg text-gray-800">{f.value_ar}</span>
        </FicheRow>
      ))}

      {/* Root siblings (naẓāʾir) → deep-links, grouped by lemma so
          homographic senses are never mixed under one root. */}
      {level.nazair && level.nazair.length > 0 && (
        <FicheRow label="النظائر">
          <span className="flex flex-col gap-2">
            {groupNazairByLemma(level.nazair).map((group) => (
              <span key={group.key} className="flex flex-col gap-1">
                {group.label && (
                  <span className="font-arabic text-sm text-gray-400">
                    {group.label}
                  </span>
                )}
                <span className="flex flex-wrap gap-1.5">
                  {group.items.map((n) => {
                    const [s, a] = n.ref.split(":");
                    return (
                      <Link
                        key={n.ref}
                        href={`/verse/${s}/${a}`}
                        title={n.ref}
                        className="rounded-md bg-gray-50 px-2 py-0.5 font-arabic text-base text-gray-700 ring-1 ring-gray-200 transition hover:bg-brand-light hover:text-brand-dark"
                      >
                        {n.word_uthmani}
                      </Link>
                    );
                  })}
                </span>
              </span>
            ))}
          </span>
        </FicheRow>
      )}
    </dl>
  );
}

/** Group naẓāʾir by lemma (keyed by `lemma`, labelled by `lemma_display`) so
 *  homographic senses are never mixed under one root. Insertion order is
 *  preserved (determinism). The lemma label is only surfaced when more than one
 *  lemma is present — a single homogeneous group needs no redundant heading. */
export function groupNazairByLemma(nazair: QlisanNazair[]): {
  key: string;
  label: string | null;
  items: QlisanNazair[];
}[] {
  const groups: { key: string; display: string | null; items: QlisanNazair[] }[] =
    [];
  const byKey = new Map<string, number>();
  for (const n of nazair) {
    const key = n.lemma ?? "";
    let idx = byKey.get(key);
    if (idx === undefined) {
      idx = groups.length;
      byKey.set(key, idx);
      groups.push({ key: key || `__${idx}`, display: n.lemma_display ?? null, items: [] });
    }
    groups[idx].items.push(n);
  }
  const multi = groups.length > 1;
  return groups.map((g) => ({
    key: g.key,
    label: multi ? g.display : null,
    items: g.items,
  }));
}
