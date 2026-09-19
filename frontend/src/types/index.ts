/**
 * Types mirroring docs/api-contract.md exactly.
 * The contract is frozen — if a shape changes here, it changes there first.
 */

export type Priority = "low" | "medium" | "high";

export type LeadStatus = "new" | "contacted" | "qualified" | "converted" | "lost";

export type ToolSource = "mcp" | "retrieval" | "local";

export type ToolStatus = "success" | "error";

export type LlmMode = "mock" | "live";

export type ChatRole = "user" | "assistant";

/** LeadOut — full lead record as returned by the backend. */
export interface Lead {
  id: number;
  name: string;
  phone: string;
  email: string | null;
  city: string | null;
  business_type: string | null;
  budget: string | null;
  requirement: string | null;
  timeline: string | null;
  monthly_queries: number | null;
  lead_score: number;
  priority: Priority;
  status: LeadStatus;
  source: string;
  created_at: string;
  updated_at: string;
}

/** One conversation turn, as sent in chat history and rendered in the UI. */
export interface ChatMessage {
  role: ChatRole;
  content: string;
}

/** One tool call performed while handling a chat turn. */
export interface ToolActivityItem {
  tool: string;
  source: ToolSource;
  status: ToolStatus;
  summary: string;
}

/** POST /api/v1/chat request body. */
export interface ChatRequest {
  message: string;
  history: ChatMessage[];
}

/** POST /api/v1/chat 200 response. */
export interface ChatResponse {
  success: true;
  reply: string;
  lead: Lead | null;
  tool_activity: ToolActivityItem[];
  retrieval_used: boolean;
  llm_mode: LlmMode;
}

/** Single-lead success envelope (GET one / POST / PATCH). */
export interface LeadResponse {
  success: true;
  lead: Lead;
}

/** Lead list success envelope (GET /api/v1/leads, admin recent-leads). */
export interface LeadListResponse {
  success: true;
  count: number;
  leads: Lead[];
}

/** Fields accepted when creating a lead (POST /api/v1/leads). */
export interface LeadCreateInput {
  name: string;
  phone: string;
  email?: string;
  city?: string;
  business_type?: string;
  budget?: string;
  requirement?: string;
  timeline?: string;
  monthly_queries?: number;
  source?: string;
}

/** Fields accepted when patching a lead (PATCH /api/v1/leads/{id}). */
export interface LeadUpdateInput {
  name?: string;
  phone?: string;
  email?: string | null;
  city?: string | null;
  business_type?: string | null;
  budget?: string | null;
  requirement?: string | null;
  timeline?: string | null;
  monthly_queries?: number | null;
  status?: LeadStatus;
  priority?: Priority;
}

/** GET /api/v1/admin/stats payload. */
export interface Stats {
  total_leads: number;
  new_leads: number;
  qualified_leads: number;
  high_priority_leads: number;
  medium_priority_leads: number;
  low_priority_leads: number;
}

export interface StatsResponse {
  success: true;
  stats: Stats;
}

/** GET /health response. */
export interface HealthResponse {
  status: string;
  app: string;
  llm_mode: LlmMode;
  version: string;
}

/** One MCP tool descriptor from GET /api/v1/admin/tools. */
export interface AdminTool {
  name: string;
  description: string;
  read_only: boolean;
}

export interface AdminToolsResponse {
  success: true;
  mcp_available: boolean;
  tools: AdminTool[];
}

/** Error envelope returned by every endpoint on failure. */
export interface ErrorEnvelope {
  success: false;
  error: {
    code: string;
    message: string;
  };
}
