import { clsx, type ClassValue } from "clsx";
import { twMerge } from "tailwind-merge";

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

export function slantLabel(score: number): string {
  if (score > 0.3) return "Liberal";
  if (score < -0.3) return "Conservative";
  return "Neutral";
}

export function slantColor(score: number): string {
  if (score > 0.3) return "#3b82f6";   // blue
  if (score < -0.3) return "#ef4444";  // red
  return "#6b7280";                     // gray
}

export function formatDate(iso: string): string {
  return new Date(iso).toLocaleDateString("en-US", {
    year: "numeric", month: "short", day: "numeric",
  });
}

export function truncate(str: string, n: number): string {
  return str.length > n ? str.slice(0, n) + "…" : str;
}
