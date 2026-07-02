import { ChevronDown } from "lucide-react";
import { forwardRef, type SelectHTMLAttributes } from "react";

import { cn } from "@/lib/utils";

/**
 * Styled native <select> — keyboard/accessibility for free, no dependency.
 * Pass <option>s as children.
 *
 * Dark mode: `color-scheme` (via the `dark:[color-scheme:dark]` utility) tells
 * the browser to render the native option popup with dark chrome. We also set an
 * explicit background/text on the trigger and its options so the closed control
 * and the popup both follow the theme tokens across browsers.
 */
const Select = forwardRef<HTMLSelectElement, SelectHTMLAttributes<HTMLSelectElement>>(
  ({ className, children, ...props }, ref) => (
    <div className="relative">
      <select
        ref={ref}
        className={cn(
          "flex h-9 w-full appearance-none rounded-md border border-input bg-background px-3 py-1 pr-8 text-sm text-foreground shadow-sm transition-colors [color-scheme:light] dark:[color-scheme:dark] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-1 focus-visible:ring-offset-background disabled:cursor-not-allowed disabled:opacity-50 [&>option]:bg-popover [&>option]:text-popover-foreground",
          className,
        )}
        {...props}
      >
        {children}
      </select>
      <ChevronDown className="pointer-events-none absolute right-2.5 top-1/2 size-4 -translate-y-1/2 text-muted-foreground" />
    </div>
  ),
);
Select.displayName = "Select";

export { Select };
