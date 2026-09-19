import type { Lead } from "../types";
import EmptyState from "./EmptyState";
import StatusBadge from "./StatusBadge";

interface LeadPanelProps {
  lead: Lead | null;
}

interface FieldProps {
  label: string;
  value: string | number | null;
  wide?: boolean;
}

function Field({ label, value, wide = false }: FieldProps) {
  const display = value === null || value === "" ? "—" : String(value);
  return (
    <div className={`lead-field${wide ? " is-wide" : ""}`}>
      <dt className="lead-label">{label}</dt>
      <dd className="lead-value">{display}</dd>
    </div>
  );
}

export default function LeadPanel({ lead }: LeadPanelProps) {
  return (
    <section className="card" aria-label="Current lead">
      <div className="card-header">
        <h2 className="card-title">Current Lead</h2>
      </div>
      {lead === null ? (
        <EmptyState
          icon="◎"
          title="No lead yet"
          description="Lead details appear here once the chat captures a contact."
        />
      ) : (
        <dl className="lead-grid">
          <Field label="Name" value={lead.name} />
          <Field label="Phone" value={lead.phone} />
          <Field label="City" value={lead.city} />
          <Field label="Business type" value={lead.business_type} />
          <Field label="Requirement" value={lead.requirement} wide />
          <Field label="Budget" value={lead.budget} />
          <Field label="Timeline" value={lead.timeline} />
          <Field label="Monthly queries" value={lead.monthly_queries} />
          <Field label="Lead score" value={lead.lead_score} />
          <div className="lead-field">
            <dt className="lead-label">Priority</dt>
            <dd className="lead-value">
              <StatusBadge kind="priority" value={lead.priority} />
            </dd>
          </div>
          <div className="lead-field">
            <dt className="lead-label">Status</dt>
            <dd className="lead-value">
              <StatusBadge kind="status" value={lead.status} />
            </dd>
          </div>
          <Field label="Source" value={lead.source} />
        </dl>
      )}
    </section>
  );
}
