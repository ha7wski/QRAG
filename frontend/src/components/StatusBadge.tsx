/**
 * Inline status badge — a parameterized generalization of the "جذر تقديري"
 * pill in LisanResult (rounded, text-xs, font-arabic, amber-tinted). Used by
 * Madār to flag the reliability of a field: a fallback root, generated text, an
 * unverified citation. Reproduces the existing Tailwind-inline pattern (no UI
 * lib). Shared here for Madār only; Lisan keeps its local copy for now.
 */
type Variant = "fallback" | "generated" | "uncertain" | "neutral";

const VARIANT_STYLES: Record<Variant, string> = {
  // Estimated root — same amber as Lisan's "جذر تقديري".
  fallback: "bg-amber-100 text-amber-800",
  // LLM-generated text — muted, clearly secondary.
  generated: "bg-gray-100 text-gray-500",
  // Present-but-unverified (e.g. parse_uncertain aṣl).
  uncertain: "bg-amber-50 text-amber-700",
  neutral: "bg-gray-100 text-gray-600",
};

export default function StatusBadge({
  variant,
  title,
  children,
}: {
  variant: Variant;
  /** Optional hover tooltip explaining the badge. */
  title?: string;
  children: React.ReactNode;
}) {
  return (
    <span
      title={title}
      className={`rounded px-2 py-0.5 font-arabic text-xs font-medium ${VARIANT_STYLES[variant]}`}
    >
      {children}
    </span>
  );
}
