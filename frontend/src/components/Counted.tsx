import { countParts, type NounForms } from "@/lib/strings";

/**
 * A counted noun whose numeral is styled apart from the noun — «<b>93</b> آية».
 *
 * The rule of العدد والمعدود lives in `countParts`, so all this decides is where
 * the emphasis goes: at 1 and 2 there is no numeral to emphasise, because the
 * noun's own form carries the number, and the emphasis moves onto the noun rather
 * than vanishing from the row.
 *
 * A caller that does not style the numeral separately wants `count()` instead.
 */
export default function Counted({
  n,
  forms,
  className = "",
}: {
  n: number;
  forms: NounForms;
  className?: string;
}) {
  const { digits, noun } = countParts(n, forms);
  if (digits === null) return <b className={className}>{noun}</b>;
  return (
    <>
      <b className={className}>{digits}</b> {noun}
    </>
  );
}
