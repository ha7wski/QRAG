import type { SelectHTMLAttributes } from "react";
import { ChevronDown } from "lucide-react";

/**
 * A native `<select>` with our own chevron. The browser's arrow sits flush
 * against the box edge and takes no padding, so it is hidden
 * (`appearance-none`) and replaced by an icon inset from the inline end — the
 * left in RTL. Every select on the site goes through here so they all match.
 *
 * `className` styles the select itself (width, size, font); the arrow's room
 * (`pe-10`) and the reset are added here.
 */
export default function SelectBox({
  className = "",
  ...props
}: SelectHTMLAttributes<HTMLSelectElement>) {
  return (
    <div className="relative">
      <select
        {...props}
        className={`appearance-none rounded-lg border border-gray-300 bg-white pe-10 ps-3 focus:border-brand focus:outline-none ${className}`}
      />
      <ChevronDown
        aria-hidden
        className="pointer-events-none absolute end-3 top-1/2 h-4 w-4 -translate-y-1/2 text-gray-500"
      />
    </div>
  );
}
