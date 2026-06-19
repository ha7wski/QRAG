import type { ReactNode } from "react";

/** Renders Arabic text right-to-left with the Quranic font. */
export default function ArabicText({
  children,
  className = "",
}: {
  children: ReactNode;
  className?: string;
}) {
  return (
    <span dir="rtl" lang="ar" className={`arabic-text ${className}`}>
      {children}
    </span>
  );
}
