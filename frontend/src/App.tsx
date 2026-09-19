import { useEffect, useState } from "react";
import ChatWindow from "./components/ChatWindow";
import LeadPanel from "./components/LeadPanel";
import ToolActivity from "./components/ToolActivity";
import { ApiError, getHealth, sendChatMessage } from "./services/api";
import type { ChatMessage, Lead, LlmMode, ToolActivityItem } from "./types";

/** A send that failed, kept so the error banner's Retry can replay it. */
interface FailedSend {
  text: string;
  history: ChatMessage[];
}

function describeError(error: unknown): string {
  if (error instanceof ApiError) {
    return error.message;
  }
  if (error instanceof Error) {
    return error.message;
  }
  return "Something went wrong while contacting the backend.";
}

export default function App() {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [lead, setLead] = useState<Lead | null>(null);
  const [activity, setActivity] = useState<ToolActivityItem[]>([]);
  const [llmMode, setLlmMode] = useState<LlmMode | null>(null);
  const [backendOnline, setBackendOnline] = useState<boolean | null>(null);
  const [sending, setSending] = useState(false);
  const [sendError, setSendError] = useState<string | null>(null);
  const [failedSend, setFailedSend] = useState<FailedSend | null>(null);

  async function checkHealth(): Promise<void> {
    try {
      const health = await getHealth();
      setBackendOnline(true);
      setLlmMode(health.llm_mode);
    } catch {
      setBackendOnline(false);
    }
  }

  useEffect(() => {
    void checkHealth();
  }, []);

  /**
   * Sends one turn and applies the response. Only appends the assistant
   * reply — the caller decides whether the user message is appended first
   * (initial send) or was already appended (retry).
   */
  async function executeSend(text: string, history: ChatMessage[]): Promise<void> {
    setSending(true);
    setSendError(null);
    try {
      const response = await sendChatMessage(text, history);
      setMessages((previous) => [...previous, { role: "assistant", content: response.reply }]);
      if (response.lead != null) {
        setLead(response.lead);
      }
      if (response.tool_activity.length > 0) {
        // Chronological order — oldest at the top, newest appended at the bottom.
        setActivity((previous) => [...previous, ...response.tool_activity]);
      }
      setLlmMode(response.llm_mode);
      setFailedSend(null);
    } catch (error) {
      setSendError(describeError(error));
      setFailedSend({ text, history });
    } finally {
      setSending(false);
    }
  }

  function handleSend(text: string): void {
    const history = messages;
    setMessages((previous) => [...previous, { role: "user", content: text }]);
    void executeSend(text, history);
  }

  function handleRetry(): void {
    if (failedSend === null || sending) {
      return;
    }
    void executeSend(failedSend.text, failedSend.history);
  }

  function handleClear(): void {
    setMessages([]);
    setActivity([]);
    setLead(null);
    setSendError(null);
    setFailedSend(null);
  }

  const statusDotClass =
    backendOnline === null ? "" : backendOnline ? "is-online" : "is-offline";
  const statusLabel =
    backendOnline === null ? "Checking…" : backendOnline ? "Online" : "Backend unavailable";

  return (
    <div className="app-shell">
      <header className="app-header">
        <div className="app-header-inner">
          <div className="brand">
            <h1 className="brand-title">Autom8r</h1>
            <p className="brand-tagline">
              Automate conversations. Qualify leads. Connect tools.
            </p>
          </div>
          <div className="header-right">
            {llmMode !== null && backendOnline === true ? (
              <span
                className={`llm-badge ${llmMode === "mock" ? "llm-badge-mock" : "llm-badge-live"}`}
              >
                {llmMode === "mock" ? "Mock LLM" : "Live LLM"}
              </span>
            ) : null}
            <span className="status-pill">
              <span className={`status-dot ${statusDotClass}`} aria-hidden="true" />
              <span className="status-text">{statusLabel}</span>
            </span>
          </div>
        </div>
      </header>

      <main className="app-main">
        <ChatWindow
          messages={messages}
          sending={sending}
          error={sendError}
          backendOnline={backendOnline}
          onSend={handleSend}
          onRetry={handleRetry}
          onRetryHealth={() => {
            void checkHealth();
          }}
          onClear={handleClear}
        />
        <div className="panel-column">
          <LeadPanel lead={lead} />
          <ToolActivity activity={activity} />
        </div>
      </main>
    </div>
  );
}
