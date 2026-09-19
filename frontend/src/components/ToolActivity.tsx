import { useEffect, useRef } from "react";
import type { ToolActivityItem } from "../types";
import EmptyState from "./EmptyState";

interface ToolActivityProps {
  activity: ToolActivityItem[];
}

export default function ToolActivity({ activity }: ToolActivityProps) {
  const listRef = useRef<HTMLUListElement>(null);

  useEffect(() => {
    const list = listRef.current;
    if (list !== null) {
      list.scrollTop = list.scrollHeight;
    }
  }, [activity]);

  return (
    <section className="card" aria-label="Tool activity">
      <div className="card-header">
        <h2 className="card-title">Tool Activity</h2>
      </div>
      {activity.length === 0 ? (
        <EmptyState
          icon="◷"
          title="No tool activity yet"
          description="Tool calls triggered by the chat will appear here."
        />
      ) : (
        <ul className="activity-list" ref={listRef}>
          {activity.map((item, index) => (
            <li className="activity-row" key={`${item.tool}-${index}`}>
              <span
                className={`activity-icon ${item.status === "success" ? "is-success" : "is-error"}`}
                role="img"
                aria-label={item.status === "success" ? "success" : "error"}
              >
                {item.status === "success" ? "✓" : "✗"}
              </span>
              <div className="activity-body">
                <div className="activity-top">
                  <span className="activity-name">{item.tool}</span>
                  <span className="activity-source">{item.source}</span>
                </div>
                <p className="activity-summary">{item.summary}</p>
              </div>
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}
