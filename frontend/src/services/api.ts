/**
 * Centralized, typed access to the Autom8r FastAPI backend.
 *
 * Every failure — network errors, non-2xx responses, malformed JSON — is
 * thrown as an ApiError with a stable `.code` and a human-readable
 * `.message`. Callers own loading state and display.
 */
import type {
  AdminToolsResponse,
  ChatMessage,
  ChatRequest,
  ChatResponse,
  ErrorEnvelope,
  HealthResponse,
  LeadCreateInput,
  LeadListResponse,
  LeadResponse,
  LeadStatus,
  LeadUpdateInput,
  Priority,
  StatsResponse,
} from "../types";

const DEFAULT_BASE_URL = "http://localhost:8000";

function resolveBaseUrl(): string {
  const fromEnv = import.meta.env.VITE_API_BASE_URL;
  if (typeof fromEnv === "string" && fromEnv.trim().length > 0) {
    return fromEnv.trim().replace(/\/+$/, "");
  }
  return DEFAULT_BASE_URL;
}

const BASE_URL = resolveBaseUrl();

export class ApiError extends Error {
  readonly code: string;
  readonly status: number | undefined;

  constructor(code: string, message: string, status?: number) {
    super(message);
    this.name = "ApiError";
    this.code = code;
    this.status = status;
  }
}

function isErrorEnvelope(value: unknown): value is ErrorEnvelope {
  if (typeof value !== "object" || value === null) {
    return false;
  }
  const record = value as Record<string, unknown>;
  if (record.success !== false) {
    return false;
  }
  const error = record.error;
  if (typeof error !== "object" || error === null) {
    return false;
  }
  const detail = error as Record<string, unknown>;
  return typeof detail.code === "string" && typeof detail.message === "string";
}

interface RequestOptions {
  method?: "GET" | "POST" | "PATCH" | "DELETE";
  body?: string;
  headers?: Record<string, string>;
}

async function request<T>(path: string, options: RequestOptions = {}): Promise<T> {
  const { method = "GET", body, headers } = options;

  const init: RequestInit = {
    method,
    headers: { "Content-Type": "application/json", ...headers },
  };
  if (body !== undefined) {
    init.body = body;
  }

  let response: Response;
  try {
    response = await fetch(`${BASE_URL}${path}`, init);
  } catch {
    throw new ApiError(
      "NETWORK_ERROR",
      `Cannot reach the Autom8r backend at ${BASE_URL}. Make sure it is running and try again.`,
    );
  }

  if (response.status === 204) {
    return undefined as unknown as T;
  }

  let parsed: unknown;
  try {
    parsed = await response.json();
  } catch {
    throw new ApiError(
      "INVALID_JSON",
      `The backend returned a response that was not valid JSON (HTTP ${response.status}).`,
      response.status,
    );
  }

  if (!response.ok) {
    if (isErrorEnvelope(parsed)) {
      throw new ApiError(parsed.error.code, parsed.error.message, response.status);
    }
    throw new ApiError(
      `HTTP_${response.status}`,
      `Request failed with HTTP ${response.status}.`,
      response.status,
    );
  }

  return parsed as T;
}

function authHeaders(token?: string): Record<string, string> {
  if (typeof token === "string" && token.length > 0) {
    return { Authorization: `Bearer ${token}` };
  }
  return {};
}

/** GET /health — liveness probe used by the header indicator. */
export async function getHealth(): Promise<HealthResponse> {
  return request<HealthResponse>("/health");
}

/** POST /api/v1/chat — send one user turn plus the full prior history. */
export async function sendChatMessage(
  message: string,
  history: ChatMessage[],
): Promise<ChatResponse> {
  const payload: ChatRequest = { message, history };
  return request<ChatResponse>("/api/v1/chat", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export interface LeadsQuery {
  status?: LeadStatus;
  priority?: Priority;
  city?: string;
  phone?: string;
  limit?: number;
  offset?: number;
}

/** GET /api/v1/leads — list leads with optional filters. */
export async function getLeads(query: LeadsQuery = {}): Promise<LeadListResponse> {
  const params = new URLSearchParams();
  if (query.status !== undefined) {
    params.set("status", query.status);
  }
  if (query.priority !== undefined) {
    params.set("priority", query.priority);
  }
  if (query.city !== undefined) {
    params.set("city", query.city);
  }
  if (query.phone !== undefined) {
    params.set("phone", query.phone);
  }
  if (query.limit !== undefined) {
    params.set("limit", String(query.limit));
  }
  if (query.offset !== undefined) {
    params.set("offset", String(query.offset));
  }
  const suffix = params.size > 0 ? `?${params.toString()}` : "";
  return request<LeadListResponse>(`/api/v1/leads${suffix}`);
}

/** GET /api/v1/leads/{id}. */
export async function getLead(id: number): Promise<LeadResponse> {
  return request<LeadResponse>(`/api/v1/leads/${id}`);
}

/** POST /api/v1/leads. */
export async function createLead(input: LeadCreateInput): Promise<LeadResponse> {
  return request<LeadResponse>("/api/v1/leads", {
    method: "POST",
    body: JSON.stringify(input),
  });
}

/** PATCH /api/v1/leads/{id}. */
export async function updateLead(id: number, input: LeadUpdateInput): Promise<LeadResponse> {
  return request<LeadResponse>(`/api/v1/leads/${id}`, {
    method: "PATCH",
    body: JSON.stringify(input),
  });
}

/** DELETE /api/v1/leads/{id} — resolves to void on 204. */
export async function deleteLead(id: number): Promise<void> {
  return request<void>(`/api/v1/leads/${id}`, { method: "DELETE" });
}

/** GET /api/v1/admin/stats — requires the admin bearer token. */
export async function getStats(token?: string): Promise<StatsResponse> {
  return request<StatsResponse>("/api/v1/admin/stats", { headers: authHeaders(token) });
}

/** GET /api/v1/admin/tools — MCP tool availability; requires the admin bearer token. */
export async function getToolActivity(token?: string): Promise<AdminToolsResponse> {
  return request<AdminToolsResponse>("/api/v1/admin/tools", { headers: authHeaders(token) });
}
