import { forwardRef } from "react";
import type { InputHTMLAttributes, SelectHTMLAttributes, TextareaHTMLAttributes } from "react";
import { cn } from "../../lib/utils";

const FIELD_CLASSES =
  "w-full rounded-md border border-neutral-200 bg-neutral-0 px-3 text-sm text-neutral-900 placeholder:text-neutral-400 transition-colors focus:border-accent-400 focus:outline-none focus:ring-2 focus:ring-accent-100 disabled:bg-neutral-50 disabled:text-neutral-400";

export const Input = forwardRef<HTMLInputElement, InputHTMLAttributes<HTMLInputElement>>(
  function Input({ className, ...props }, ref) {
    return <input ref={ref} className={cn(FIELD_CLASSES, "h-10", className)} {...props} />;
  },
);

export const Textarea = forwardRef<
  HTMLTextAreaElement,
  TextareaHTMLAttributes<HTMLTextAreaElement>
>(function Textarea({ className, ...props }, ref) {
  return <textarea ref={ref} className={cn(FIELD_CLASSES, "py-2", className)} {...props} />;
});

export const Select = forwardRef<HTMLSelectElement, SelectHTMLAttributes<HTMLSelectElement>>(
  function Select({ className, children, ...props }, ref) {
    return (
      <select ref={ref} className={cn(FIELD_CLASSES, "h-10", className)} {...props}>
        {children}
      </select>
    );
  },
);

export function Label({ children, htmlFor }: { children: string; htmlFor?: string }) {
  return (
    <label htmlFor={htmlFor} className="mb-1.5 block text-sm font-medium text-neutral-700">
      {children}
    </label>
  );
}
