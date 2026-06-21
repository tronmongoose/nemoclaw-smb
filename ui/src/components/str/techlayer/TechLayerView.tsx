/** Sponsor x portal matrix for the tech-layer judging view (data-portal="stack"). */

import { useEffect, useRef, useState } from "react";
import { cn } from "../../../lib/utils";
import type { StrInteraction, StrInteractionsResponse, StrSegment } from "../../../types";
import { SectionLabel } from "../shared";
import { StackGraph } from "../StackGraph";
import {
  SPONSOR_MAP,
  PORTAL_ORDER,
  PORTAL_LABELS,
  opMatchesCell,
  type SponsorRow,
  type SponsorCell,
} from "./sponsorMap";
import { usePoll } from "../../../hooks/usePoll";

/** Count entries for a given sponsor + segment + cell (total and live-only). */
function countCell(
  entries: StrInteraction[],
  sponsor: string,
  seg: StrSegment,
  cell: SponsorCell,
): { total: number; live: number } {
  let total = 0;
  let live = 0;
  for (const e of entries) {
    if (e.sponsor !== sponsor) continue;
    if (e.segment !== seg) continue;
    if (!opMatchesCell(e.op, cell)) continue;
    total++;
    if (e.mode === "live") live++;
  }
  return { total, live };
}

/** Empty cell when a sponsor does not participate in a portal. */
function EmptyCell(): JSX.Element {
  return (
    <td className="border-l border-border px-3 py-3 text-center font-mono text-xs text-muted-foreground/40">
      -
    </td>
  );
}

/** Count badge with optional live-glow and heartbeat dot. */
function CountBadge({
  total,
  live,
  flashing,
  ariaLabel,
}: {
  total: number;
  live: number;
  flashing: boolean;
  ariaLabel: string;
}): JSX.Element {
  const hasLive = live > 0;
  return (
    <span
      aria-label={ariaLabel}
      className={cn(
        "inline-flex items-center gap-1 rounded-[var(--radius)] border px-1.5 py-0.5 font-mono text-[0.65rem] tabular-nums",
        hasLive
          ? "border-primary/40 text-primary"
          : "border-border text-muted-foreground",
        flashing && "animate-flash",
      )}
    >
      {hasLive && (
        <span className="h-1 w-1 rounded-full bg-primary animate-heartbeat" aria-hidden="true" />
      )}
      {total} calls
    </span>
  );
}

/** Body cell for a sponsor that participates in a given portal. */
function ActiveCell({
  cell,
  entries,
  sponsor,
  seg,
}: {
  cell: SponsorCell;
  entries: StrInteraction[];
  sponsor: string;
  seg: StrSegment;
}): JSX.Element {
  const { total, live } = countCell(entries, sponsor, seg, cell);
  const prevRef = useRef(total);
  const [flashing, setFlashing] = useState(false);

  useEffect(() => {
    if (total > prevRef.current) {
      setFlashing(true);
      const t = setTimeout(() => setFlashing(false), 1700);
      prevRef.current = total;
      return () => clearTimeout(t);
    }
    prevRef.current = total;
  }, [total]);

  return (
    <td
      className={cn(
        "border-l border-border px-3 py-3 align-top",
        flashing && "animate-flash",
      )}
    >
      <div className="flex flex-col gap-1">
        <span className="font-mono text-xs font-medium text-foreground">{cell.capability}</span>
        <span className="font-mono text-[0.65rem] text-muted-foreground">{cell.problem}</span>
        <CountBadge
          total={total}
          live={live}
          flashing={false}
          ariaLabel={`${sponsor} ${PORTAL_LABELS[seg]}: ${total} calls${live > 0 ? `, ${live} live` : ""}`}
        />
      </div>
    </td>
  );
}

/** Leading cell for each sponsor row: name, kind, blurb. */
function SponsorRowHeader({ row }: { row: SponsorRow }): JSX.Element {
  return (
    <th
      scope="row"
      className="w-44 border-r border-border px-3 py-3 text-left align-top"
    >
      <span className="block font-serif text-sm font-semibold text-foreground">{row.sponsor}</span>
      <span className="block font-mono text-[0.65rem] text-muted-foreground">
        {row.kind}, {row.blurb}
      </span>
    </th>
  );
}

/** Sponsor x portal matrix table. */
function SponsorMatrix({ entries }: { entries: StrInteraction[] }): JSX.Element {
  return (
    <div className="overflow-x-auto rounded-[var(--radius)] border border-border bg-card">
      <table className="min-w-full border-collapse text-sm" role="grid" aria-label="Sponsor portal matrix">
        <thead>
          <tr className="border-b border-border">
            <th scope="col" className="w-44 px-3 py-2 text-left">
              <span className="font-mono text-[0.65rem] uppercase tracking-[0.18em] text-muted-foreground">
                Sponsor
              </span>
            </th>
            {PORTAL_ORDER.map((seg) => (
              <th
                key={seg}
                scope="col"
                className="border-l border-border px-3 py-2 text-left"
              >
                <span className="font-mono text-[0.65rem] uppercase tracking-[0.18em] text-muted-foreground">
                  {PORTAL_LABELS[seg]}
                </span>
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {SPONSOR_MAP.map((row, i) => (
            <tr
              key={row.id}
              className={cn("border-b border-border last:border-0", i % 2 === 1 && "bg-background/30")}
            >
              <SponsorRowHeader row={row} />
              {PORTAL_ORDER.map((seg) => {
                const cell = row.byPortal[seg];
                return cell ? (
                  <ActiveCell
                    key={seg}
                    cell={cell}
                    entries={entries}
                    sponsor={row.sponsor}
                    seg={seg}
                  />
                ) : (
                  <EmptyCell key={seg} />
                );
              })}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

/** Top-level tech-layer view: matrix + live verification graph. No title (parent provides it). */
export function TechLayerView(): JSX.Element {
  const { data } = usePoll<StrInteractionsResponse>("/str/interactions?limit=1000", 2500);
  const entries = data?.entries ?? [];

  return (
    <div className="flex flex-col gap-8">
      <SponsorMatrix entries={entries} />
      <div>
        <SectionLabel>Live verification</SectionLabel>
        <StackGraph />
      </div>
    </div>
  );
}
