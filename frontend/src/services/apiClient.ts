/**
 * Axios-based HTTP client. Base URL is read from VITE_API_BASE_URL at build time.
 * Do not hardcode localhost anywhere else in the codebase.
 */
import axios, { AxiosError } from "axios";
import type { ErrorResponse } from "@/types/api";

const BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000";

export const apiClient = axios.create({
  baseURL: BASE_URL,
  headers: { "Content-Type": "application/json" },
  timeout: 30_000,
});

// ── Typed error extraction ──────────────────────────────────────────────────────

export class ApiError extends Error {
  constructor(
    public readonly code: string,
    message: string,
    public readonly detail: Record<string, unknown> = {},
    public readonly status: number = 0,
  ) {
    super(message);
    this.name = "ApiError";
  }
}

export function parseAxiosError(err: unknown): ApiError {
  if (err instanceof ApiError) return err;

  if (err instanceof AxiosError) {
    const body = err.response?.data as Partial<ErrorResponse> | undefined;
    return new ApiError(
      body?.error ?? "NETWORK_ERROR",
      body?.message ?? err.message ?? "An unexpected error occurred.",
      body?.detail ?? {},
      err.response?.status ?? 0,
    );
  }

  if (err instanceof Error) {
    return new ApiError("UNKNOWN_ERROR", err.message);
  }

  return new ApiError("UNKNOWN_ERROR", "An unexpected error occurred.");
}

// ── Response unwrapper ──────────────────────────────────────────────────────────

/** Extracts `.data` from a `SuccessResponse<T>` envelope. */
export function unwrap<T>(envelope: { data: T }): T {
  return envelope.data;
}
