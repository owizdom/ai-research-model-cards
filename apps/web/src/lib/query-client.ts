"use client";
import { QueryClient } from "@tanstack/react-query";

let browserQueryClient: QueryClient | undefined;

export function getQueryClient(): QueryClient {
  if (typeof window === "undefined") {
    return new QueryClient({ defaultOptions: { queries: { staleTime: 60_000 } } });
  }
  if (!browserQueryClient) {
    browserQueryClient = new QueryClient({ defaultOptions: { queries: { staleTime: 60_000 } } });
  }
  return browserQueryClient;
}
