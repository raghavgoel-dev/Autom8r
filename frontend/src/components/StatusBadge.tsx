type BadgeKind = "priority" | "status";

type BadgeTone =
  | "slate"
  | "amber"
  | "green"
  | "indigo"
  | "sky"
  | "violet"
  | "teal"
  | "rose";

/** Priority palette is fixed by the design contract: low/medium/high. */
const PRIORITY_TONES: Record<string, BadgeTone> = {
  low: "slate",
  medium: "amber",
  high: "green",
};

/** Status palette is deliberately distinct from the priority palette. */
const STATUS_TONES: Record<string, BadgeTone> = {
  new: "indigo",
  contacted: "sky",
  qualified: "violet",
  converted: "teal",
  lost: "rose",
};

interface StatusBadgeProps {
  kind: BadgeKind;
  value: string;
}

export default function StatusBadge({ kind, value }: StatusBadgeProps) {
  const tones = kind === "priority" ? PRIORITY_TONES : STATUS_TONES;
  const tone = tones[value] ?? "slate";
  return <span className={`badge badge-${tone}`}>{value}</span>;
}
