import { useEffect, useRef, useState } from "react";
import type { ChatMessage as ChatMessageData } from "../types";
import ChatMessage from "./ChatMessage";
import EmptyState from "./EmptyState";

interface ChatWindowProps {
  messages: ChatMessageData[];
  sending: boolean;
  error: string | null;
  backendOnline: boolean | null;
  onSend: (text: string) => void;
  onRetry: () => void;
  onRetryHealth: () => void;
  onClear: () => void;
}

export default function ChatWindow({
  messages,
  sending,
  error,
  backendOnline,
  onSend,
  onRetry,
  onRetryHealth,
  onClear,
}: ChatWindowProps) {
  const [draft, setDraft] = useState("");
  const listRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const list = listRef.current;
    if (list !== null) {
      list.scrollTop = list.scrollHeight;
    }
  }, [messages, sending, error, backendOnline]);

  const trimmed = draft.trim();
  const canSend = trimmed.length > 0 && !sending && backendOnline !== false;

  function submit(): void {
    if (!canSend) {
      return;
    }
    onSend(trimmed);
    setDraft("");
  }

  const header = (
    <div className="card-header">
      <h2 className="card-title">Chat</h2>
      <button
        type="button"
        className="btn btn-ghost"
        onClick={onClear}
        disabled={sending || messages.length === 0}
      >
        Clear
      </button>
    </div>
  );

  if (backendOnline === false) {
    return (
      <section className="card chat-card" aria-label="Chat">
        {header}
        <div className="chat-offline">
          <EmptyState
            icon="⚠"
            title="Backend unavailable"
            description="Start the backend and retry."
          />
          <button type="button" className="btn btn-primary" onClick={onRetryHealth}>
            Retry
          </button>
        </div>
      </section>
    );
  }

  return (
    <section className="card chat-card" aria-label="Chat">
      {header}

      <div className="message-list" ref={listRef}>
        {messages.length === 0 && !sending ? (
          <EmptyState
            icon="💬"
            title="Start a conversation"
            description="Ask about our products, or tell me what you want to automate"
          />
        ) : null}

        {messages.map((message, index) => (
          <ChatMessage key={index} message={message} />
        ))}

        {sending ? (
          <div className="message-row is-assistant">
            <div className="message-meta">Autom8r</div>
            <div className="bubble bubble-assistant thinking-bubble">
              <span>Autom8r is thinking</span>
              <span className="typing-dots" aria-hidden="true">
                <span />
                <span />
                <span />
              </span>
            </div>
          </div>
        ) : null}
      </div>

      {error !== null ? (
        <div className="error-banner" role="alert">
          <span className="error-banner-text">{error}</span>
          <button
            type="button"
            className="btn btn-primary btn-sm"
            onClick={onRetry}
            disabled={sending}
          >
            Retry
          </button>
        </div>
      ) : null}

      <div className="composer">
        <textarea
          className="composer-input"
          rows={2}
          placeholder="Type your message…"
          aria-label="Message"
          value={draft}
          onChange={(event) => setDraft(event.target.value)}
          onKeyDown={(event) => {
            if (event.key === "Enter" && !event.shiftKey) {
              event.preventDefault();
              submit();
            }
          }}
        />
        <button type="button" className="btn btn-primary" onClick={submit} disabled={!canSend}>
          Send
        </button>
      </div>
    </section>
  );
}
