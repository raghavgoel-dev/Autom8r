import type { ChatMessage as ChatMessageData } from "../types";

interface ChatMessageProps {
  message: ChatMessageData;
}

export default function ChatMessage({ message }: ChatMessageProps) {
  const isUser = message.role === "user";
  return (
    <div className={`message-row ${isUser ? "is-user" : "is-assistant"}`}>
      <div className="message-meta">{isUser ? "You" : "Autom8r"}</div>
      <div className={`bubble ${isUser ? "bubble-user" : "bubble-assistant"}`}>
        {message.content}
      </div>
    </div>
  );
}
